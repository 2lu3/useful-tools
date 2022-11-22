from pynput.mouse import Listener

click_count = 0


def on_click(x, y, _, pressed):
    global click_count
    if pressed == True:
        print(x, y)
        click_count += 1
    if click_count >= 10:
        return False


with Listener(on_click=on_click) as listener:
    listener.join()
