from .app import *


def main():
    app = QApplication(sys.argv)

    console_locals = {}
    console_locals.update(locals())
    console_locals.update(globals())

    console = PythonConsole(locals=console_locals)
    console.eval_queued()

    settings_manager = SettingsManager()
    settings_manager.read_settings()

    browser = Browser(settings_manager, app=app, console=console)
    browser.show()

    console.interpreter.locals['browser'] = browser

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
