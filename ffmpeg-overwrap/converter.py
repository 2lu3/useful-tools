from subprocess import Popen
import os
import pickle
import glob
import time


# from_file_types = ['MOV', 'MTS']
# from_file_types = ['MTS']
# from_file_types = ['MOV']
from_file_types = ["mp4"]
to_file_type = "mp4"

configurations = [
    "-c:v h264_amf",
    #'-c:v hevc_amf',
    #'-vcodec libx264',
    #'-c:a copy',
    #'-crf 30',
    #'-vf scale=-1:720',
    "-b:v 1000k",
    "-b:a 128k",
    #'-an',
    #'-tag:v hvc1',
    "-vtag avc1",
]

# from_file_types = ['MTS']
# to_file_type = 'MOV'
# configurations = [
#        '-f mov',
#        #'-c:a copy',
#        ]


class MovieConverter:
    def __init__(self):
        self.in_folder = "input"
        self.out_folder = "output"
        # dict('path', 'start', 'finished')
        self.movie_paths = []
        self.log_movie_paths = None
        self.movie_converted = []
        self.log_movie_converted = []
        self.lock_file_name = "lock"
        self.movie_paths_pickle_name = "pickle_path.pickle"
        self.movie_converted_pickle_name = "pickle_converted.pickle"
        self.to_file_type = to_file_type
        self.from_file_types = from_file_types

    def update_log_file(self):
        with open(self.movie_paths_pickle_name, "wb") as f:
            pickle.dump(self.movie_paths, f)
        with open(self.movie_converted_pickle_name, "wb") as f:
            pickle.dump(self.movie_converted, f)

    def load_log_file(self):
        if os.path.exists(self.lock_file_name):
            print("reading log files")
            with open(self.movie_paths_pickle_name, "rb") as f:
                self.log_movie_paths = pickle.load(f)
            with open(self.movie_converted_pickle_name, "rb") as f:
                self.log_movie_converted = pickle.load(f)
        else:
            print("no lock file")
            print("not reading log files")
            self.log_movie_paths = None

            # lockファイルを作成
            with open(self.lock_file_name, "w") as f:
                f.write("You looked at me!")

    def search_data_folder(self):
        self.movie_paths = []
        for from_type in self.from_file_types:
            self.movie_paths.extend(
                glob.glob(self.in_folder + "/**/*." + from_type, recursive=True)
            )

        print("found these files")
        for file_path in self.movie_paths:
            print(file_path)

    def create_to_path(self, from_path):
        return (
            self.out_folder
            + from_path.split(".")[0].removeprefix(self.in_folder)
            + "."
            + self.to_file_type
        )

    def create_command(self, from_path):
        command = 'ffmpeg -i "' + from_path + '"'
        for conf in configurations:
            command += " " + conf
        command += ' "' + self.create_to_path(from_path) + '"'
        return command

    def ffmpeg(self, path):
        command = self.create_command(path)
        print("command", command)
        popen = Popen(command)
        popen.wait()

    def run(self):
        self.load_log_file()
        self.search_data_folder()

        if self.log_movie_paths is not None:
            print("cotinue restored working")
            self.movie_paths = self.log_movie_paths
            self.movie_converted = self.log_movie_converted
            self.movie_converted.extend(
                [
                    False
                    for _ in range(len(self.movie_paths) - len(self.movie_converted))
                ]
            )
        else:
            print("start new task")
            self.movie_converted = [False for _ in self.movie_paths]

        for i in range(len(self.movie_paths)):
            from_path = self.movie_paths[i]
            to_path = self.create_to_path(from_path)

            if self.movie_converted[i] == True:
                print("passed " + to_path)
                continue

            # 既にファイルが有る場合
            if os.path.exists(to_path):
                # ファイルを削除
                os.remove(to_path)
                time.sleep(1)

            # 子フォルダまで作成されていない場合
            os.makedirs(to_path.removesuffix(os.path.basename(to_path)), exist_ok=True)

            time.sleep(1)
            self.ffmpeg(from_path)
            self.movie_converted[i] = True

            self.update_log_file()

        print("all done")
        os.remove(self.lock_file_name)


def main():
    converter = MovieConverter()
    converter.run()


if __name__ == "__main__":
    main()
