import asyncio
import os
from playwright.async_api import async_playwright
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScreenshotService:
    def __init__(self, app_url="http://localhost:5001", output_path="static/image.png"):
        self.app_url = app_url
        self.output_path = output_path
        self.browser = None
        self.page = None
        
    async def initialize(self):
        """Initialize the browser and page"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-web-security', '--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page()
        
        # Set viewport to 800x480 with device scale factor for better quality
        await self.page.set_viewport_size({"width": 800, "height": 480, "deviceScaleFactor": 2})
        
    async def take_screenshot(self):
        """Take a screenshot of the departure board"""
        try:
            logger.info("Taking screenshot of departure board...")
            
            # Navigate to the departure board
            await self.page.goto(self.app_url, wait_until="networkidle")
            
            # Wait for the page to fully load and data to be displayed
            await self.page.wait_for_selector('.departure-board', timeout=10000)
            await self.page.wait_for_selector('.service-item', timeout=10000)
            
            # Wait a bit more to ensure all animations and updates are complete
            await asyncio.sleep(2)
            
            # Take screenshot with exact 800x480 dimensions
            await self.page.screenshot(
                path=self.output_path,
                clip={"x": 0, "y": 0, "width": 800, "height": 480},
                type='png'
            )
            
            logger.info(f"Screenshot saved to {self.output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return False
            
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
            
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Synchronous wrapper for easier integration with Flask
def take_departure_board_screenshot():
    """Synchronous function to take a screenshot of the departure board"""
    async def async_screenshot():
        async with ScreenshotService() as service:
            return await service.take_screenshot()
            
    return asyncio.run(async_screenshot())

if __name__ == "__main__":
    # Test the screenshot service
    success = take_departure_board_screenshot()
    print(f"Screenshot {'successful' if success else 'failed'}")
