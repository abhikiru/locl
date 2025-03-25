// DOM Elements
const loginSection = document.getElementById('login-section');
const mainContent = document.getElementById('main-content');
const usernameInput = document.getElementById('username-input');
const passwordInput = document.getElementById('password-input');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');
const loggedInUser = document.getElementById('logged-in-user');
const textInput = document.getElementById('text-input');
const actionMode = document.getElementById('action-mode');
const submitBtn = document.getElementById('submit-btn');
const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history');
const clipboardManagerSection = document.getElementById('clipboard-manager-section');
const copiedTextSection = document.getElementById('copied-text-section');
const copiedTextList = document.getElementById('copied-text-list');
const clearCopiedTextBtn = document.getElementById('clear-copied-text');
const clipboardManagerBtn = document.getElementById('clipboard-manager-btn');
const copiedTextBtn = document.getElementById('copied-text-btn');

let currentUsername = null;
let pollingInterval = null; // For polling the copied text history

// Login Logic
loginBtn.addEventListener('click', () => {
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username || !password) {
    loginError.textContent = 'Please enter both username and password.';
    return;
  }

  fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        currentUsername = username;
        loginSection.style.display = 'none';
        mainContent.style.display = 'block';
        loggedInUser.textContent = `Logged in as: ${username}`;
        loadHistory(); // Load history after login
        showClipboardManager(); // Show Clipboard Manager by default
      } else {
        loginError.textContent = 'Invalid credentials. Please try again.';
      }
    })
    .catch(error => {
      console.error('Error during login:', error);
      loginError.textContent = 'Failed to connect to server. Please try again.';
    });
});

// Toggle Sections
function showClipboardManager() {
  clipboardManagerSection.style.display = 'block';
  copiedTextSection.style.display = 'none';
  clipboardManagerBtn.classList.add('active');
  copiedTextBtn.classList.remove('active');
  // Stop polling when leaving the Copied Text Viewer
  if (pollingInterval) {
    clearInterval(pollingInterval);
    pollingInterval = null;
  }
}

function showCopiedText() {
  clipboardManagerSection.style.display = 'none';
  copiedTextSection.style.display = 'block';
  clipboardManagerBtn.classList.remove('active');
  copiedTextBtn.classList.add('active');
  loadCopiedText(); // Load copied text history when showing the section
  // Start polling to refresh the copied text history every 2 seconds
  if (!pollingInterval) {
    pollingInterval = setInterval(loadCopiedText, 2000);
  }
}

clipboardManagerBtn.addEventListener('click', showClipboardManager);
copiedTextBtn.addEventListener('click', showCopiedText);

// Load history from server (Clipboard Manager)
function loadHistory() {
  fetch(`/fetch-history/${currentUsername}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        console.log('Clipboard Manager history loaded:', data.history);
        data.history.forEach(item => addToHistory(item));
      } else {
        console.error('Failed to load Clipboard Manager history:', data.message);
      }
    })
    .catch(error => console.error('Error loading history:', error));
}

// Load copied text history from server
function loadCopiedText() {
  fetch(`/fetch-copied-text/${currentUsername}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        console.log('Copied text history loaded:', data.history);
        copiedTextList.innerHTML = ''; // Clear existing items
        if (data.history.length === 0) {
          console.log('No copied text history found.');
          const emptyItem = document.createElement('li');
          emptyItem.textContent = 'No copied text yet...';
          copiedTextList.appendChild(emptyItem);
        } else {
          data.history.forEach(item => addToCopiedText(item));
        }
      } else {
        console.error('Failed to load copied text history:', data.message);
      }
    })
    .catch(error => console.error('Error loading copied text history:', error));
}

// Add to Clipboard Manager History
function addToHistory(text) {
  const listItem = document.createElement('li');
  listItem.className = 'history-item';

  const textSpan = document.createElement('span');
  textSpan.textContent = text;
  listItem.appendChild(textSpan);

  const copyBtn = document.createElement('button');
  copyBtn.className = 'copy-btn';
  copyBtn.textContent = 'Copy';
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Text copied to clipboard!');
    });
  });
  listItem.appendChild(copyBtn);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-btn';
  deleteBtn.textContent = '✕';
  deleteBtn.addEventListener('click', () => {
    listItem.remove();
    deleteHistoryFromServer(text);
  });
  listItem.appendChild(deleteBtn);

  historyList.insertBefore(listItem, historyList.firstChild); // Add to top (LIFO)
  enforceHistoryLimit();
}

// Add to Copied Text History
function addToCopiedText(text) {
  const listItem = document.createElement('li');
  listItem.className = 'copied-text-item';

  const textSpan = document.createElement('span');
  textSpan.textContent = text;
  listItem.appendChild(textSpan);

  const copyBtn = document.createElement('button');
  copyBtn.className = 'copy-btn';
  copyBtn.textContent = 'Copy';
  copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(text).then(() => {
      alert('Text copied to clipboard!');
    });
  });
  listItem.appendChild(copyBtn);

  const deleteBtn = document.createElement('button');
  deleteBtn.className = 'delete-btn';
  deleteBtn.textContent = '✕';
  deleteBtn.addEventListener('click', () => {
    listItem.remove();
    deleteCopiedTextFromServer(text);
  });
  listItem.appendChild(deleteBtn);

  copiedTextList.insertBefore(listItem, copiedTextList.firstChild); // Add to top (LIFO)
}

// Enforce max 10 history items (Clipboard Manager)
function enforceHistoryLimit() {
  const items = historyList.getElementsByTagName('li');
  while (items.length > 10) {
    const lastItem = items[items.length - 1];
    const text = lastItem.querySelector('span').textContent;
    deleteHistoryFromServer(text);
    lastItem.remove();
  }
}

// Save history to server (Clipboard Manager)
function saveHistoryToServer(text) {
  fetch(`/update-history/${currentUsername}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).catch(error => console.error('Error saving history:', error));
}

// Delete history item from server (Clipboard Manager)
function deleteHistoryFromServer(text) {
  fetch(`/delete-history/${currentUsername}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).catch(error => console.error('Error deleting history:', error));
}

// Delete copied text item from server
function deleteCopiedTextFromServer(text) {
  fetch(`/delete-copied-text/${currentUsername}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }).catch(error => console.error('Error deleting copied text:', error));
}

// Clear History (Clipboard Manager)
clearHistoryBtn.addEventListener('click', () => {
  historyList.innerHTML = '';
  fetch(`/clear-history/${currentUsername}`, {
    method: 'POST',
  }).catch(error => console.error('Error clearing history:', error));
});

// Clear Copied Text History
clearCopiedTextBtn.addEventListener('click', () => {
  copiedTextList.innerHTML = '';
  fetch(`/clear-copied-text/${currentUsername}`, {
    method: 'POST',
  }).catch(error => console.error('Error clearing copied text history:', error));
});

// Submit Button Logic (Clipboard Manager)
submitBtn.addEventListener('click', () => {
  const text = textInput.value.trim();
  const mode = actionMode.value;

  if (!text) {
    alert('Please enter some text!');
    return;
  }

  if (mode === 'copy' || mode === 'both') {
    // Send the text to the server to copy it to the server's system clipboard
    fetch("/update-clipboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: currentUsername, text }),
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === 'success') {
          alert('Text copied to server clipboard!');
        } else {
          alert('Failed to copy text to server clipboard.');
        }
      })
      .catch(error => console.error("Error updating clipboard on server:", error));
  }

  if (mode === 'history' || mode === 'both') {
    addToHistory(text);
    saveHistoryToServer(text);
  }

  textInput.value = ''; // Clear input after submission
});