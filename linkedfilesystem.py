import json

class LinkedBlock:
    def __init__(self, block_size):
        self.data = bytearray(block_size)
        self.next_block_idx = None

    def reset(self):
        self.next_block_idx = None

class INode:
    def __init__(self):
        self.reset()

    def reset(self, fs=None):
        if fs and self.start_block_idx is not None:
            self.free_chain(fs)
        self.used = False
        self.file_type = ""
        self.size = 0
        self.start_block_idx = None

    def free_chain(self, fs):
        current_idx = self.start_block_idx
        while current_idx is not None:
            block = fs.blocks[current_idx]
            next_idx = block.next_block_idx
            block.reset()
            fs.free_blocks.add(current_idx)
            current_idx = next_idx
        self.start_block_idx = None
        self.size = 0

    def get_data(self, fs):
        if self.start_block_idx is None:
            return b''
        data = bytearray()
        current_idx = self.start_block_idx
        while current_idx is not None:
            block = fs.blocks[current_idx]
            data.extend(block.data)
            current_idx = block.next_block_idx
        return bytes(data[:self.size])

    def write_bytes(self, fs, data: bytes):
        self.free_chain(fs)
        self.size = len(data)
        if not data:
            return

        remaining_data = memoryview(data)
        first_block_idx = fs.alloc_block()
        self.start_block_idx = first_block_idx
        current_block_idx = first_block_idx

        while remaining_data:
            current_block = fs.blocks[current_block_idx]
            chunk = remaining_data[:fs.BLOCK_SIZE]
            current_block.data[:len(chunk)] = chunk
            remaining_data = remaining_data[len(chunk):]

            if remaining_data:
                next_block_idx = fs.alloc_block()
                current_block.next_block_idx = next_block_idx
                current_block_idx = next_block_idx
            else:
                current_block.next_block_idx = None

class Directory:
    def __init__(self, fs, name, parent=None, inode_idx=None):
        self.fs = fs
        self.name = name
        self.parent = parent
        if inode_idx is None:
            self.inode_idx = fs.alloc_inode()
            inode = fs.inodes[self.inode_idx]
            inode.file_type = "directory"
            inode.used = True
            self.update_entries({})
        else:
            self.inode_idx = inode_idx

    def get_entries(self):
        inode = self.fs.inodes[self.inode_idx]
        data = inode.get_data(self.fs)
        if not data:
            return {}
        return json.loads(data.decode("utf-8"))

    def update_entries(self, entries):
        inode = self.fs.inodes[self.inode_idx]
        data = json.dumps(entries).encode("utf-8")
        inode.write_bytes(self.fs, data)

    def get_path(self):
        if self.parent is None:
            return "/"
        path = []
        curr = self
        while curr.parent is not None:
            path.append(curr.name)
            curr = curr.parent
        return "/" + "/".join(reversed(path))

class LinkedFileSystem:
    def __init__(self, num_blocks, block_size):
        self.NUM_BLOCKS = num_blocks
        self.BLOCK_SIZE = block_size
        self.NUM_INODES = num_blocks // 1

        self.blocks = [LinkedBlock(block_size) for _ in range(num_blocks)]
        self.free_blocks = set(range(num_blocks))

        self.inodes = [INode() for _ in range(self.NUM_INODES)]
        self.free_inodes = set(range(self.NUM_INODES))

        self.root = Directory(self, "/")
        self.current_dir = self.root

    def alloc_block(self):
        if not self.free_blocks:
            raise RuntimeError("No free blocks available")
        return self.free_blocks.pop()

    def alloc_inode(self):
        if not self.free_inodes:
            raise RuntimeError("No free inodes available")
        idx = self.free_inodes.pop()
        self.inodes[idx].reset()
        return idx

    def get_dir(self, path: str):
        if path == "/":
            return self.root

        if path.startswith("/"):
            dir_obj = self.root
            parts = path.strip("/").split("/")
        else:
            dir_obj = self.current_dir
            parts = path.strip().split("/")

        for part in parts:
            if part in (".", ""):
                continue
            if part == "..":
                if dir_obj.parent is not None:
                    dir_obj = dir_obj.parent
                continue

            entries = dir_obj.get_entries()
            if part not in entries:
                print(f"Directory '{part}' not found.")
                return None

            inode_idx = entries[part]
            inode = self.inodes[inode_idx]

            if inode.file_type != "directory":
                print(f"Path error: '{part}' is not a directory")
                return None
            
            dir_obj = Directory(name=part, parent=dir_obj, inode_idx=inode_idx, fs=self)
        return dir_obj

    def change_directory(self, path):
        if not path:
            self.current_dir = self.root
            return
        target_dir = self.get_dir(path[0])
        if target_dir:
            self.current_dir = target_dir

    def make_directory(self, path):
        if not path:
            print("mkdir: missing operand")
            return
        name = path[0]
        if "/" not in name:
            parent_dir = self.current_dir
            dirname = name
        else:
            p = name.rpartition("/")
            parent_dir = self.get_dir(p[0] or "/")
            if parent_dir is None:
                return
            dirname = p[-1]

        entries = parent_dir.get_entries()
        if dirname in entries:
            print(f"mkdir: '{dirname}' already exists")
            return
        
        new_dir = Directory(self, dirname, parent=parent_dir)
        entries[dirname] = new_dir.inode_idx
        parent_dir.update_entries(entries)

    def remove_directory(self, path):
        if not path:
            return
        dir_to_remove = self.get_dir(path[0])
        if dir_to_remove is None or dir_to_remove.parent is None:
            print("rmdir: cannot remove root directory or non-existent directory")
            return
        
        if dir_to_remove.get_entries():
            print(f"rmdir: failed to remove '{dir_to_remove.name}': Directory not empty")
            return
        
        parent_entries = dir_to_remove.parent.get_entries()
        inode_idx = parent_entries.pop(dir_to_remove.name)
        
        self.inodes[inode_idx].reset(self)
        self.free_inodes.add(inode_idx)
        dir_to_remove.parent.update_entries(parent_entries)

    def make_file(self, path):
        if len(path) < 2:
            print("mkfile: Not enough arguments")
            return
        name, content = path[0], " ".join(path[1:])
        if "/" not in name:
            parent_dir = self.current_dir
            fname = name
        else:
            p = name.rpartition("/")
            parent_dir = self.get_dir(p[0] or "/")
            if parent_dir is None:
                return
            fname = p[-1]

        entries = parent_dir.get_entries()
        if fname in entries:
            print(f"mkfile: '{fname}' already exists")
            return
        
        inode_idx = self.alloc_inode()
        inode = self.inodes[inode_idx]
        inode.file_type = "file"
        inode.used = True
        inode.write_bytes(self, content.encode("utf-8"))
        entries[fname] = inode_idx
        parent_dir.update_entries(entries)

    def remove_file(self, path):
        if not path:
            print("rm: Not enough arguments")
            return
        name = path[0]
        if "/" not in name:
            parent_dir = self.current_dir
            fname = name
        else:
            p = name.rpartition("/")
            parent_dir = self.get_dir(p[0] or "/")
            if parent_dir is None:
                return
            fname = p[-1]

        entries = parent_dir.get_entries()
        if fname in entries:
            inode_idx = entries.pop(fname)
            self.inodes[inode_idx].reset(self) 
            self.free_inodes.add(inode_idx)
            parent_dir.update_entries(entries)
        else:
            print(f"rm: cannot remove '{fname}': No such file or directory")

    def move(self, path):
        if len(path) < 2:
            print("mv: Not enough arguments")
            return
        src_path, dest_path = path[0], path[1]

        if "/" not in src_path:
            src_dir = self.current_dir
            src_name = src_path
        else:
            p = src_path.rpartition("/")
            src_dir = self.get_dir(p[0] or "/")
            if src_dir is None:
                return
            src_name = p[-1]
            
        dest_dir = self.get_dir(dest_path)
        if dest_dir is None:
            print(f"mv: target '{dest_path}' is not a directory")
            return

        src_entries = src_dir.get_entries()
        dest_entries = dest_dir.get_entries()

        if src_name not in src_entries:
            print(f"mv: cannot stat '{src_path}': No such file or directory")
            return
        if src_name in dest_entries:
            print(f"mv: cannot move '{src_name}' to '{dest_path}': Destination path already exists")
            return
        
        inode_idx = src_entries.pop(src_name)
        dest_entries[src_name] = inode_idx
        
        src_dir.update_entries(src_entries)
        dest_dir.update_entries(dest_entries)

    def _cat(self, path):
        if not path:
            return
        file_path = path[0]
        
        if "/" not in file_path:
            parent_dir = self.current_dir
            fname = file_path
        else:
            p = file_path.rpartition("/")
            parent_dir = self.get_dir(p[0] or "/")
            if parent_dir is None:
                return
            fname = p[-1]
        
        entries = parent_dir.get_entries()
        if fname not in entries:
            print(f"cat: '{fname}': No such file or directory")
            return

        inode_idx = entries[fname]
        inode = self.inodes[inode_idx]
        if inode.file_type != "file":
            print(f"cat: '{fname}': Is a directory")
            return
            
        data = inode.get_data(self)
        return data.decode('utf-8')

    def cat(self, path):
        data = self._cat(path)
        print(data)

    def list_directory(self, path=None):
        dir_to_list = self.current_dir
        if path:
            dir_to_list = self.get_dir(path[0])
        if dir_to_list is None:
            return

        entries = dir_to_list.get_entries()
        output = []
        for name in sorted(entries.keys()):
            inode_idx = entries[name]
            inode = self.inodes[inode_idx]
            if inode.file_type == "file":
                output.append(f"\033[32m{name}\033[0m")             
            elif inode.file_type == "directory":
                output.append(f"\033[34m{name}\033[0m")         
        if output:
             print(" ".join(output))
