import subprocess
import tomllib


def main():
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    file = config["pictype"]["style"] + ".py"

    subprocess.run(["uv", "run", file], check=True)


if __name__ == "__main__":
    main()
