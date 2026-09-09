import sys
import unicodedata


def sanitize(text):
    parts = []
    for ch in text:
        cat = unicodedata.category(ch
        if cat == "Cf":
            continue
        if cat == "Cc":
            continue
        parts.append(ch
    return "".join(parts


def main(argv:
    for path in argv:
        with open(path, encoding="utf-8") as fh:
            src = fh.read(
        cleaned = sanitize(src
        if cleaned != src:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(cleaned
            print("sanitized", path
        else:
            print("clean", path


if __name__ == "__main__":
    main(sys.argv[1:])