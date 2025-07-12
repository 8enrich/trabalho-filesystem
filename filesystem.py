from directory import Directory
from inode import INode  # File


class FileSystem:
    def __init__(self, num_blocks, block_size):
        self.NUM_BLOCKS = num_blocks
        self.BLOCK_SIZE = block_size
        self.NUM_INODES = num_blocks // INode.MAX_BLOCKS

        self.blocks = [bytearray(block_size) for _ in range(num_blocks)]
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
            dir = self.root
            parts = path.strip("/").split("/")
        else:
            dir = self.current_dir
            parts = path.strip().split("/")

        for part in parts:
            if part in (".", ""):
                continue

            if part == "..":
                if dir.parent is not None:
                    dir = dir.parent
                continue

            entries = dir.get_entries()

            if part not in entries:
                print(f"Directory '{part}' not found.")
                return None

            inode_idx = entries[part]
            inode = self.inodes[inode_idx]

            if inode.file_type != "directory":
                print(f"Path error: '{part}' is not a directory")
                return None

            dir = Directory(name=part, parent=dir, inode_idx=inode_idx, fs=self)

        return dir

    def change_directory(self, path):
        if not path:
            return self.root
        self.current_dir = self.get_dir(path[0]) or self.current_dir

    def make_directory(self, path):
        if not path:
            print("mkdir: missing operand")
            return

        name = path[0]

        if "/" not in name:
            dir = self.current_dir
            dirname = name
        else:
            p = name.rpartition("/")
            dir = self.get_dir(p[0])
            if dir is None:
                return
            dirname = p[-1]

        entries = dir.get_entries()
        if dirname in entries:
            print(f"mkdir: '{dirname}' already exists")
            return

        new_dir = Directory(self, dirname, parent=dir)
        entries[dirname] = new_dir.inode_idx
        dir.update_entries(entries)

    def remove_directory(self, path):
        dir = self.get_dir(path[0])
        if dir is None or dir.parent is None:
            return
        entries = dir.parent.get_entries()
        if dir.name in entries:
            inode_idx = entries.pop(dir.name)
            self.free_inodes.add(inode_idx)
            self.inodes[inode_idx].reset()
            dir.parent.update_entries(entries)

    def make_file(self, path):
        if len(path) < 2:
            print("mkfile: Not enough arguments")
            return

        name, content = path[0], " ".join(path[1:])

        if "/" not in name:
            dir = self.current_dir
            fname = name
        else:
            p = name.rpartition("/")
            dir = self.get_dir(p[0])
            if dir is None:
                return
            fname = p[-1]

        entries = dir.get_entries()
        if fname in entries:
            print(f"mkfile: '{fname}' already exists")
            return

        inode_idx = self.alloc_inode()
        inode = self.inodes[inode_idx]
        inode.file_type = "file"
        inode.write_bytes(self, content.encode("utf-8"))
        entries[fname] = inode_idx
        dir.update_entries(entries)

    def move(self, path):
        if len(path) < 2:
            print("mv: Not enough arguments")
            return

        name, new_dir_name = path[0], " ".join(path[1:])

        if "/" not in name:
            dir = self.current_dir
            fname = name
        else:
            p = name.rpartition("/")
            dir = self.get_dir(p[0])
            if dir is None:
                return
            fname = p[-1]

        new_dir = self.get_dir(new_dir_name)
        if new_dir is None:
            return

        entries = dir.get_entries()
        new_entries = new_dir.get_entries()
        if fname not in entries:
            print(f"mv: '{fname}' not founded")
            return
        new_entries[fname] = entries.pop(fname)
        new_dir.update_entries(new_entries)
        dir.update_entries(entries)

    def remove_file(self, path):
        if not path:
            print("rm: Not enough arguments")
            return

        name = path[0]

        if "/" not in name:
            dir = self.current_dir
            fname = name
        else:
            p = name.rpartition("/")
            dir = self.get_dir(p[0])
            if dir is None:
                return
            fname = p[-1]

        entries = dir.get_entries()
        if fname in entries:
            inode_idx = entries.pop(fname)
            self.free_inodes.add(inode_idx)
            self.inodes[inode_idx].reset()
            dir.update_entries(entries)            

    def _cat(self, path):
        p = path[0].rpartition("/")
        dir = self.get_dir(p[0])
        if dir is None:
            return
        entries = dir.get_entries()
        if p[-1] not in entries:
            print(f"cat: '{p[-1]}' not found")
            return
        inode_idx = entries[p[-1]]
        data = self.inodes[inode_idx].get_data(self)
        return data.decode("utf-8")

    def cat(self, path):
        data = self._cat(path)
        if data:
            print(data)

    def list_directory(self, path=None):
        dir = self.current_dir if not path else self.get_dir(path[0])

        if dir is None:
            return

        entries = dir.get_entries()
        string = ""
        for name in sorted(entries.keys()):
            inode_idx = entries[name]
            inode = self.inodes[inode_idx]
            if inode.file_type == "file":
                string += f"\033[32m{name}\033[0m "
            if inode.file_type == "directory":
                string += f"\033[34m{name}\033[0m "
        if string:
            print(string)
