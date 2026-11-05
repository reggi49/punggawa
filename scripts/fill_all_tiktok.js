async (page) => {
  // 1. Select Category
  const catBtn = page.locator('#\\:r36\\:_button');
  if (await catBtn.count() > 0) {
    await catBtn.click();
    await page.waitForTimeout(400);
    const socialOption = page.locator('[role="option"]:has-text("Social Networking")');
    if (await socialOption.count() > 0) {
      await socialOption.click();
    }
  }

  // 2. Fill Description
  const desc = page.locator('#\\:r37\\:_textArea');
  if (await desc.count() > 0) {
    await desc.fill('Manage and schedule social media video posts across channels.');
  }

  // 3. Fill Terms of Service URL
  const tos = page.locator('#\\:r38\\:_input');
  if (await tos.count() > 0) {
    await tos.fill('https://sosial.bogorstore.com/terms');
  }

  // 4. Fill Privacy Policy URL
  const priv = page.locator('#\\:r39\\:_input');
  if (await priv.count() > 0) {
    await priv.fill('https://sosial.bogorstore.com/privacy');
  }

  // 5. Check Platform Web checkbox (:r3a:)
  const webCb = page.locator('#\\:r3a\\:');
  if (await webCb.count() > 0 && !(await webCb.isChecked())) {
    await webCb.click();
  }

  // 6. Fill Web URL (:r4f:_input)
  await page.waitForTimeout(500);
  const webUrl = page.locator('#\\:r4f\\:_input');
  if (await webUrl.count() > 0) {
    await webUrl.fill('https://sosial.bogorstore.com');
  }

  return { success: true };
}
