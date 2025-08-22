let activeTabs = {}; // tabId → true/false

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.action === "enableCaptions") {
    activeTabs[msg.tabId] = true;
    chrome.scripting.executeScript({
      target: { tabId: msg.tabId },
      func: (tabId) => window.startCaptions(tabId),
      args: [msg.tabId]
    });
  }

  if (msg.action === "disableCaptions") {
    activeTabs[msg.tabId] = false;
    chrome.scripting.executeScript({
      target: { tabId: msg.tabId },
      func: () => window.stopCaptions()
    });
  }
});
