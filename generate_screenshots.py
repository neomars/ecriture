import sys
from playwright.sync_api import sync_playwright

def generate_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Set viewport size
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        # 1. Load Application
        page.goto("http://localhost:5000")
        page.wait_for_timeout(1500)

        # Select French if not already selected
        page.select_option("#lang-select", "fr")
        page.wait_for_timeout(1000)

        # Click a scene to load editor content and make it look nice
        try:
            page.click("text=Netherfield Park is let at last")
        except Exception:
            pass
        page.wait_for_timeout(500)

        # Take French Main Screenshot
        page.screenshot(path="images/screenshot_main_fr.png")
        print("Generated images/screenshot_main_fr.png")

        # 2. Switch to English
        page.select_option("#lang-select", "en")
        page.wait_for_timeout(1000)
        page.screenshot(path="images/screenshot_main_en.png")
        print("Generated images/screenshot_main_en.png")

        # 3. Switch back to French to view Plot Grid
        page.select_option("#lang-select", "fr")
        page.wait_for_timeout(500)
        page.click("text=Grille d'intrigue")
        page.wait_for_timeout(1000)
        page.screenshot(path="images/screenshot_plot_grid.png")
        print("Generated images/screenshot_plot_grid.png")

        # 4. Click a scene to get back to editor
        page.click("text=Chapter 1")
        page.wait_for_timeout(500)
        try:
            page.click("text=Netherfield Park is let at last")
        except Exception:
            pass
        page.wait_for_timeout(500)

        # Click Project Settings
        page.click('button[onclick="openSettingsModal()"]')
        page.wait_for_timeout(500)

        # Toggle lock checkbox in settings modal
        page.check("#settings-lock-input")
        page.wait_for_timeout(500)

        # Close modal
        page.click('button[onclick="saveProjectSettings()"]')
        page.wait_for_timeout(1000)

        # Take Locked screen screenshot
        page.screenshot(path="images/screenshot_locked.png")
        print("Generated images/screenshot_locked.png")

        # Unlock the project so it is left in clean state for next runs
        page.click('button[onclick="openSettingsModal()"]')
        page.wait_for_timeout(500)
        page.uncheck("#settings-lock-input")
        page.wait_for_timeout(500)
        page.click('button[onclick="saveProjectSettings()"]')
        page.wait_for_timeout(500)

        context.close()
        browser.close()

if __name__ == "__main__":
    generate_all()
