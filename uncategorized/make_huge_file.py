from tqdm import tqdm

with open("test.txt", "w") as f:
    for i in range(10):
        print(i)
        for _ in range(10**100):
            f.write("hello")
