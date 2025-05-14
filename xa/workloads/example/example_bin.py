if __name__ == "__main__":
    import sys
    file = sys.argv[1]  # example input param
    print("Example test")
    with open(file, "r") as f:
        data = f.read()
    with open("example.txt", "w") as f:
        f.write(f"Example test data: {data}")