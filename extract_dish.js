const { chromium } = require('playwright');
const fs = require('fs');

async function run() {
  console.log('Connecting to remote browser...');
  const browser = await chromium.connect({ wsEndpoint: 'ws://192.168.15.166:3000/' });
  const context = await browser.newContext();
  const page = await context.newPage();
  
  const url = 'https://www.foodbag.be/nl/recept?dishId=a0MJv00000FNr9RMAT';
  
  try {
    console.log(`Navigating to ${url}...`);
    await page.goto(url, { waitUntil: 'load' });

    // 1. Handle Cookie Banner immediately
    console.log('Checking for cookie banner...');
    const cookieBtn = await page.locator('#onetrust-accept-btn-handler').waitFor({ timeout: 5000 }).catch(() => null);
    if (cookieBtn) {
      await cookieBtn.click();
      console.log('Cookie banner accepted.');
    }

    // 2. Wait for actual content to appear in the DOM
    // We look for common recipe keywords or structural elements
    console.log('Waiting for dish data to hydrate in DOM...');
    
    // Try waiting for an element that typically contains ingredients or directions
    // Since we don't know the exact class, we search for text patterns like "Ingrediënten" or "Bereiding"
    await page.waitForFunction(
      () => document.body.innerText.includes('Ingrediënten') || 
            document.body.innerText.includes('Bereiding') || 
            document.body.innerText.includes('Ingredients'), 
      { timeout: 30000 }
    );

    console.log('Content detected! Extracting...');

    // Give it a moment to settle
    await page.waitForTimeout(2000);

    const content = await page.content();
    fs.writeFileSync('rendered_dish.html', content);
    
    const text = await page.innerText('body');
    fs.writeFileSync('rendered_dish.txt', text);

    console.log('Successfully saved rendered HTML and Text.');

  } catch (e) {
    console.error('Error during extraction:', e.message);
    // Save the current state anyway to see where it got stuck
    const failedContent = await page.content();
    fs.writeFileSync('failed_state.html', failedContent);
    console.log('Saved failure state to failed_state.html');
  } finally {
    await browser.close();
  }
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
