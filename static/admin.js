const loginForm = document.getElementById('loginForm');
const loginSection = document.getElementById('loginSection');
const postsSection = document.getElementById('postsSection');
const postsContainer = document.getElementById('postsContainer');
const logoutButton = document.getElementById('logoutButton');

async function checkAdmin() {
  const res = await fetch('/admin/check');
  const data = await res.json();
  if (data.logged_in) {
    loginSection.style.display = 'none';
    postsSection.style.display = 'block';
    fetchPosts();
  } else {
    loginSection.style.display = 'block';
    postsSection.style.display = 'none';
  }
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const password = document.getElementById('password').value;
  const formData = new FormData();
  formData.append('password', password);

  const res = await fetch('/admin/login', {
    method: 'POST',
    body: formData
  });

  if (res.ok) {
    checkAdmin();
  } else {
    alert('Wrong password!');
  }
});

logoutButton.addEventListener('click', async () => {
  await fetch('/admin/logout', { method: 'POST' });
  checkAdmin();
});

async function fetchPosts() {
  postsContainer.innerHTML = '<p>Loading posts...</p>';
  const res = await fetch('/admin/posts');
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
      <button onclick="approvePost(${post.id})">Approve</button>
      <button onclick="deletePost(${post.id})" style="background:red;color:white;">Delete</button>
    `;
    postsContainer.appendChild(postDiv);
  });
}

async function approvePost(id) {
  const res = await fetch(`/admin/approve/${id}`, { method: 'POST' });
  if (res.ok) {
    fetchPosts();
  } else {
    alert('Approve failed!');
  }
}

async function deletePost(id) {
  const res = await fetch(`/admin/delete/${id}`, { method: 'DELETE' });
  if (res.ok) {
    fetchPosts();
  } else {
    alert('Delete failed!');
  }
}

checkAdmin();
