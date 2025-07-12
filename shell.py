import os
from filesystem import FileSystem
from linkedfilesystem import LinkedFileSystem

class Shell:
    def __init__(self, fs: FileSystem | LinkedFileSystem) -> None:
        self.fs = fs
        self.commands = {
            "ls": self.fs.list_directory,
            "cd": self.fs.change_directory,
            "rmdir": self.fs.remove_directory,
            "rm": self.fs.remove_file,
            "mkfile": self.fs.make_file,
            "mkdir": self.fs.make_directory,
            "exit": self.exit_,
            "cat": self.fs.cat,
            "clear": self.clear,
            "mv": self.fs.move,
        }

    def start(self):
        while True:
            user_input = input(f"{self.fs.current_dir.get_path()} > ").strip().split()
            if not user_input:
                continue
            func = self.commands.get(user_input[0])
            if func is None:
                print(f"Command not found: {user_input[0]}")
                continue
            func(user_input[1:])

    def exit_(self, _):
        exit()

    def clear(self, _):
        os.system("clear")
