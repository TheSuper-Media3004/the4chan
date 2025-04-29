const boardSelect = document.getElementById('board');
const postsContainer = document.getElementById('postsContainer');
const newPostForm = document.getElementById('newPostForm');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const themeToggleBtn = document.getElementById('themeToggleBtn');

function cleanBoardValue(board) {
  return board.replace(/^\/+|\/+$/g, '');
}

async function fetchPosts(board) {
  postsContainer.innerHTML = '<p>Loading posts...</p>';
  const cleanBoard = cleanBoardValue(board);
  const res = await fetch(`/posts/${cleanBoard}`);
  if (!res.ok) {
    postsContainer.innerHTML = '<p>Error loading posts.</p>';
    return;
  }
  const posts = await res.json();

  postsContainer.innerHTML = '';
  posts.forEach(post => {
    const postDiv = document.createElement('div');
    postDiv.className = 'post-item';
    postDiv.innerHTML = `
      <p><strong>User ${post.user_id}</strong> (${post.board}):</p>
      <p>${post.content}</p>
      ${post.image ? `<img src="/uploads/${post.image}" alt="Image">` : ''}
      <p>Status: ${post.is_approved ? 'Approved' : 'Pending'}</p>
    `;
    postsContainer.appendChild(postDiv);
  });
}


boardSelect.addEventListener('change', () => {
  fetchPosts(boardSelect.value);
});

// Submit new post
newPostForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const formData = new FormData(newPostForm);
  formData.append('board', boardSelect.value);

  const res = await fetch('/post', {
    method: 'POST',
    body: formData
  });

  if (res.ok) {
    newPostForm.reset();
    fetchPosts(boardSelect.value);
  } else {
    let errorMsg = 'Post failed.';
    try {
      const data = await res.json();
      if (data && data.message) errorMsg = data.message;
    } catch (e) {}
    alert(errorMsg);
  }
});

fetchPosts(boardSelect.value);

clearHistoryBtn.addEventListener('click', async () => {
  const res = await fetch('/clear_history', {
    method: 'POST'
  });

  if (res.ok) {
    postsContainer.innerHTML = '';
    alert('History cleared successfully.');
  } else {
    alert('Failed to clear history.');
  }
});


function toggleTheme() {
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const isDarkMode = document.body.classList.toggle('dark-mode');
  themeToggleBtn.innerHTML = isDarkMode ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
}

// Initialize theme toggle button with correct icon
window.onload = function() {
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const isDarkMode = document.body.classList.contains('dark-mode');
  themeToggleBtn.innerHTML = isDarkMode ? '<i class="fas fa-moon"></i>' : '<i class="fas fa-sun"></i>';
};

// Add event listener for theme toggle
themeToggleBtn.addEventListener('click', toggleTheme);

// Add event listener for creating a new board
const createBoardForm = document.getElementById('createBoardForm');

createBoardForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const boardName = document.getElementById('boardName').value;
  const nsfwSetting = document.getElementById('nsfwSetting').checked;

  const res = await fetch('/create_board', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ board: boardName, nsfw: nsfwSetting })
  });

  if (res.ok) {
    alert('Board created successfully.');
    // Optionally, refresh the board list
    fetchBoards();
  } else {
    alert('Failed to create board.');
  }
});

// Function to fetch and display boards
async function fetchBoards() {
  const res = await fetch('/boards');
  if (!res.ok) {
    alert('Error loading boards.');
    return;
  }
  const boards = await res.json();

  const boardSelect = document.getElementById('board');
  boardSelect.innerHTML = '';
  boards.forEach(board => {
    const option = document.createElement('option');
    option.value = board.name;
    option.textContent = `${board.name} (${board.nsfw ? 'NSFW' : 'SFW'})`;
    boardSelect.appendChild(option);
  });
}

// Call fetchBoards on page load to populate the board list
window.onload = function() {
  fetchBoards();
};

// Gemini 2.0 Chatbot Integration
const geminiChatBtn = document.getElementById('geminiChatBtn');
const geminiChatWindow = document.getElementById('geminiChatWindow');
const closeGeminiChat = document.getElementById('closeGeminiChat');
const geminiChatForm = document.getElementById('geminiChatForm');
const geminiChatInput = document.getElementById('geminiChatInput');
const geminiChatMessages = document.getElementById('geminiChatMessages');

if (geminiChatBtn && geminiChatWindow && closeGeminiChat && geminiChatForm && geminiChatInput && geminiChatMessages) {
  geminiChatBtn.addEventListener('click', () => {
    geminiChatWindow.style.display = 'flex';
    geminiChatInput.focus();
  });
  closeGeminiChat.addEventListener('click', () => {
    geminiChatWindow.style.display = 'none';
  });
  geminiChatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userMsg = geminiChatInput.value.trim();
    if (!userMsg) return;
    appendGeminiMessage('You', userMsg);
    geminiChatInput.value = '';
    geminiChatInput.disabled = true;
    try {
      const res = await fetch('/gemini_chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      let botMsg = 'No response.';
      if (data && data.message) {
        botMsg = data.message;
      } else if (data && data.error) {
        botMsg = 'Error: ' + data.error;
      }
      appendGeminiMessage('Gemini', botMsg);
    } catch (err) {
      appendGeminiMessage('Gemini', 'Sorry, there was an error connecting to Gemini.');
    }
    geminiChatInput.disabled = false;
    geminiChatInput.focus();
  });
}
function appendGeminiMessage(sender, text) {
  const msgDiv = document.createElement('div');
  msgDiv.style.marginBottom = '0.5rem';
  msgDiv.innerHTML = `<strong>${sender}:</strong> <span>${escapeHtml(text)}</span>`;
  geminiChatMessages.appendChild(msgDiv);
  geminiChatMessages.scrollTop = geminiChatMessages.scrollHeight;
}
function escapeHtml(unsafe) {
  return unsafe.replace(/[&<"'>]/g, function(m) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#039;'}[m];
  });
}
