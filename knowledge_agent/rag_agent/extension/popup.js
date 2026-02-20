document.getElementById("askBtn").addEventListener("click", () => {
  const query = document.getElementById("userQuery").value;

  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        function: getPageContent
      },
      async (injectionResults) => {
        const pageContent = injectionResults[0].result;

        const response = await fetch("http://localhost:8000/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            text: pageContent,
            query: query
          })
        });

        const data = await response.json();
        document.getElementById("responseBox").innerText = data.answer;
      }
    );
  });
});

function getPageContent() {
  return document.body.innerText;
}
