import pygetwindow as gw


def main() -> None:
    ws = gw.getAllWindows()
    keys = ("Tibia", "Proyector", "Projector", "OBS")
    for w in ws:
        title = (w.title or "").strip()
        if not title:
            continue
        if any(k.lower() in title.lower() for k in keys):
            try:
                print(
                    repr(title),
                    "->",
                    (w.left, w.top, w.width, w.height),
                    "min=", getattr(w, "isMinimized", None),
                    "max=", getattr(w, "isMaximized", None),
                )
            except Exception as e:
                print(repr(title), "-> err", e)


if __name__ == "__main__":
    main()
