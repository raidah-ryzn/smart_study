// script.js — mengambil data dari backend Python (/api/dashboard) lalu merender UI

// Check authentication first
async function checkAuth() {
  try {
    const response = await fetch('/api/auth/status');
    const data = await response.json();
    
    if (!data.authenticated) {
      window.location.href = '/login';
      return false;
    }
    window.currentUserId = data.user_id || null;
    window.currentUserRole = (data.role || 'user').toLowerCase();
    return true;
  } catch (error) {
    console.error('Auth check error:', error);
    window.location.href = '/login';
    return false;
  }
}

function showAlert(message, type = 'default') {
  if (!message) return;
  if (type === 'error') {
    alert(`Error: ${message}`);
  } else if (type === 'success') {
    alert(`Sukses: ${message}`);
  } else {
    alert(message);
  }
}

function handleLogout() {
  logout();
}

// Load dashboard data
async function loadDashboard() {
  try {
    const res = await fetch("/api/dashboard");
    
    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }
    
    const data = await res.json();

    document.getElementById("welcome-title").textContent =
      `Selamat datang kembali, ${data.user.name}!`;

    // Update user name in topbar
    const userNameEl = document.querySelector('.user-name');
    if (userNameEl) {
      userNameEl.textContent = data.user.name;
    }

    // Update avatar text
    const avatarEl = document.querySelector('.avatar');
    if (avatarEl && data.user.name) {
      const initials = data.user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
      avatarEl.textContent = initials || 'U';
    }

    renderCategories(data.categories);
    renderCourses(data.courses);
    // store baseline progress for merges with task-driven updates
    window.__baseProgress = data.progress || { completed: 0, inProgress: 0, notStarted: 0 };
    // load courses from backend (fallback to local sample if none)
    await loadCoursesFromServer();
    // initialize task controls after DOM nodes exist
    initializeCourseActions();
    setupAddCourseButton();
    renderEvents(eventData);
    renderDonut(data.progress);
    renderLegend(data.progress);
    renderTasks(data.tasks);
    // merge assignments and in-memory tasks into progress display
    await refreshProgressFromServer();
  } catch (error) {
    console.error('Load dashboard error:', error);
  }
}

// Logout function
async function logout() {
  try {
    const response = await fetch('/api/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      window.location.href = '/login';
    }
  } catch (error) {
    console.error('Logout error:', error);
  }
}

function renderCategories(categories) {
  const el = document.getElementById("category-row");
  el.innerHTML = categories.map(c => `
    <div class="category-card">
      <div class="cat-title">${c.icon} ${c.name}</div>
      <div class="cat-progress">${c.watched}/${c.total} Video</div>
    </div>
  `).join("");
}

const courseLibraryData = [
  {
    type: 'video',
    title: 'Belajar Flask dari Nol',
    author: 'Mentor Aulia',
    duration: '1 jam 20 menit',
    description: 'Video tutorial lengkap membuat aplikasi web dengan Flask dan MySQL.',
    resource_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
  },
  {
    type: 'ebook',
    title: 'Panduan Desain UI/UX Modern',
    author: 'Tim MyCourse',
    duration: '48 halaman',
    description: 'E-book materi desain antarmuka dengan warna dan layout modern.',
    resource_url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
  },
  {
    type: 'video',
    title: 'Pengantar Pemrograman Python',
    author: 'Dewayani',
    duration: '2 jam 10 menit',
    description: 'Seri video dasar Python untuk pemula yang ingin cepat memahami logika.',
    resource_url: 'https://www.youtube.com/watch?v=rfscVS0vtbw'
  },
  {
    type: 'ebook',
    title: 'E-book Strategi Belajar Efektif',
    author: 'Julia Prima',
    duration: '36 halaman',
    description: 'Materi ringkas untuk merancang jadwal belajar dan mencapai target cepat.',
    resource_url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
  },
  {
    type: 'video',
    title: 'Workshop CSS dan Animasi',
    author: 'Rizky',
    duration: '1 jam 45 menit',
    description: 'Video praktek langsung membuat dashboard dengan animasi halus.',
    resource_url: 'https://www.youtube.com/watch?v=UB1O30fR-EE'
  },
  {
    type: 'ebook',
    title: 'Kumpulan Soal dan Latihan',
    author: 'MyCourse Labs',
    duration: '60 halaman',
    description: 'E-book berisi soal latihan dan pembahasan untuk topik pemrograman.',
    resource_url: 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'
  }
];

const courseList = [];

const eventData = [
  {
    id: 1,
    title: 'Webinar Product Design Aesthetic',
    type: 'webinar',
    speaker: 'Sabrina Putri',
    date: '12 Agustus 2026',
    time: '19:00 WIB',
    price: 'Gratis',
    description: 'Sesi livestream interaktif via Zoom untuk membahas strategi desain produk modern dan praktik UI/UX.',
    link: 'https://zoom.us/j/1234567890',
    tags: ['Webinar', 'Gratis']
  },
  {
    id: 2,
    title: 'Workshop Flask dan Database',
    type: 'webinar',
    speaker: 'Rizki Santoso',
    date: '15 Agustus 2026',
    time: '14:00 WIB',
    price: 'Rp 75.000',
    description: 'Workshop berbayar dengan koneksi Zoom, live coding, dan Q&A untuk membangun aplikasi Python full-stack.',
    link: 'https://zoom.us/j/9876543210',
    tags: ['Webinar', 'Bayar']
  },
  {
    id: 3,
    title: 'Grup Belajar Data Science',
    type: 'group',
    speaker: 'Tim Mentor',
    date: 'Setiap Senin',
    time: '20:00 WIB',
    price: 'Gratis',
    description: 'Grup belajar mingguan via Zoom dan chat untuk mengerjakan studi kasus bersama peserta lain.',
    link: 'https://zoom.us/j/1122334455',
    tags: ['Grup Belajar', 'Gratis']
  },
  {
    id: 4,
    title: 'Grup Belajar UI/UX Modern',
    type: 'group',
    speaker: 'Nadia',
    date: 'Setiap Rabu',
    time: '18:30 WIB',
    price: 'Gratis',
    description: 'Kolaborasi proyek desain dan sesi feedback kelompok untuk mempercepat skill UI/UX.',
    link: 'https://zoom.us/j/5566778899',
    tags: ['Grup Belajar', 'Bayar']
  }
];

function renderCourses(courses) {
  const el = document.getElementById("course-row");
  el.innerHTML = courses.map(c => `
    <div class="course-card">
      <div class="course-thumb"></div>
      <div class="course-body">
        <div class="course-cat">${c.category}</div>
        <div class="course-title">${c.title}</div>
        <div class="course-meta">${c.author} • ${c.duration}</div>
        <div class="progress-bar">
          <div class="progress-fill" style="width:${c.progress}%"></div>
        </div>
      </div>
    </div>
  `).join("");
}

function renderCourseLibrary(courses) {
  const el = document.getElementById("courses-library");
  el.innerHTML = courses.map(c => {
    const assignmentCount = c.assignment_count || 0;
    const isCompleted = Boolean(c.completed);
    const completeLabel = isCompleted ? 'Selesai' : 'Tandai Selesai';
    const completeDisabled = isCompleted ? 'disabled' : '';
    const addTaskDisabled = isCompleted ? 'disabled' : '';
    return `
      <div class="course-library-card ${isCompleted ? 'course-completed' : ''}" data-type="${c.type}" data-course-id="${c.id || ''}" data-resource-url="${c.resource_url || ''}">
        <div class="course-library-thumb">
          <div class="course-library-type">${c.type === 'video' ? 'Video' : 'E-book'}</div>
          ${isCompleted ? '<span class="course-status-badge">Selesai</span>' : ''}
        </div>
        <div class="course-library-body">
          <div class="course-library-title">${c.title}</div>
          <div class="course-library-meta">
            <span>${c.author || ''}</span>
            <span>${c.duration || ''}</span>
          </div>
          <div class="course-library-description">${c.description || ''}</div>
          <div class="course-library-assignments">${assignmentCount} tugas tersedia</div>
          <div class="course-task-controls">
            <span class="task-count">Tugas: <strong class="task-count-val">${assignmentCount}</strong></span>
            <div class="task-control-btns">
              <button class="add-task-btn" ${addTaskDisabled}>+Tugas</button>
              <button class="complete-task-btn" ${isCompleted ? 'disabled' : ''}>${isCompleted ? 'Selesai' : 'Selesai'}</button>
            </div>
          </div>
          <div class="course-actions">
            <button class="btn-primary open-course-btn">Buka</button>
            <button class="btn-secondary detail-course-btn">Detail</button>
            <button class="btn-secondary complete-course-btn" ${completeDisabled}>${completeLabel}</button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function renderEvents(events) {
  const el = document.getElementById('events-list');
  if (!el) return;
  el.innerHTML = events.map(e => `
    <div class="event-card" data-event-id="${e.id}">
      <div class="event-card-top">
        <span class="event-badge ${e.price === 'Gratis' ? 'badge-free' : 'badge-paid'}">${e.price}</span>
        <span class="event-type">${e.type === 'webinar' ? 'Webinar' : 'Grup Belajar'}</span>
      </div>
      <div class="event-title">${e.title}</div>
      <div class="event-meta">
        <span>${e.speaker}</span>
        <span>${e.date} • ${e.time}</span>
      </div>
      <div class="event-description">${e.description}</div>
      <div class="event-actions">
        <button class="btn-primary open-event-btn" data-event-id="${e.id}">Gabung via Zoom</button>
        <button class="btn-secondary detail-event-btn" data-event-id="${e.id}">Lihat Detail</button>
      </div>
    </div>
  `).join('');
  setupEventActions();
}

function setupEventActions() {
  const buttons = document.querySelectorAll('.event-card .open-event-btn, .event-card .detail-event-btn');
  buttons.forEach(button => {
    const eventId = button.dataset.eventId;
    const eventItem = eventData.find(e => String(e.id) === String(eventId));
    if (!eventItem) return;

    if (button.classList.contains('open-event-btn')) {
      button.addEventListener('click', () => {
        window.open(eventItem.link, '_blank');
      });
    }

    if (button.classList.contains('detail-event-btn')) {
      button.addEventListener('click', () => {
        openEventModal(eventItem);
      });
    }
  });
}

function openEventModal(eventItem) {
  const modal = document.getElementById('event-modal');
  const modalTitle = document.getElementById('event-modal-title');
  const modalType = document.getElementById('event-modal-type');
  const modalBody = document.getElementById('event-modal-body');

  modalTitle.textContent = eventItem.title;
  modalType.textContent = `${eventItem.type === 'webinar' ? 'Webinar' : 'Grup Belajar'} • ${eventItem.price}`;
  modalBody.innerHTML = `
    <p><strong>Pembicara:</strong> ${eventItem.speaker}</p>
    <p><strong>Waktu:</strong> ${eventItem.date} • ${eventItem.time}</p>
    <p>${eventItem.description}</p>
    <div class="modal-event-actions">
      <button class="btn-primary" onclick="window.open('${eventItem.link}', '_blank')">Join Zoom</button>
      <button class="btn-secondary" onclick="navigator.clipboard.writeText('${eventItem.link}').then(()=>alert('Link Zoom disalin'))">Salin Link</button>
    </div>
  `;
  modal.classList.remove('hidden');
}

function closeEventModal() {
  const modal = document.getElementById('event-modal');
  if (modal) modal.classList.add('hidden');
}

function initializeCourseActions() {
  const cards = document.querySelectorAll('.course-library-card');
  cards.forEach((card) => {
    const addBtn = card.querySelector('.add-task-btn');
    const completeCourseBtn = card.querySelector('.complete-course-btn');
    const openBtn = card.querySelector('.open-course-btn');
    const detailBtn = card.querySelector('.detail-course-btn');
    const courseId = card.dataset.courseId;
    const courseType = card.dataset.type;
    const resourceUrl = card.dataset.resourceUrl || '';
    const courseTitle = card.querySelector('.course-library-title')?.textContent || '';

    if (!courseId) {
      if (addBtn) addBtn.disabled = true;
      if (completeCourseBtn) completeCourseBtn.disabled = true;
    }

    if (addBtn) {
      addBtn.addEventListener('click', async () => {
        if (!courseId) return;
        const taskTitle = prompt('Judul tugas baru untuk materi ini', `Tugas baru untuk ${courseTitle}`);
        if (!taskTitle) return;

        try {
          const res = await fetch(`/api/courses/${courseId}/assignments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: taskTitle })
          });
          if (res.status === 201) {
            showAlert('Tugas berhasil ditambahkan.', 'success');
            await loadCoursesFromServer();
            await refreshProgressFromServer();
            if (document.getElementById('assignments-page') && !document.getElementById('assignments-page').classList.contains('hidden')) {
              await loadAssignments();
            }
          } else {
            const d = await res.json();
            showAlert(d.message || 'Gagal menambahkan tugas', 'error');
          }
        } catch (err) {
          console.error(err);
          showAlert('Gagal menghubungi server', 'error');
        }
      });
    }

    if (openBtn) {
      openBtn.addEventListener('click', () => {
        openResourceModal(courseTitle, courseType, resourceUrl);
      });
    }

    if (detailBtn) {
      detailBtn.addEventListener('click', () => {
        openResourceModal(courseTitle, courseType, resourceUrl);
      });
    }

    if (completeCourseBtn) {
      completeCourseBtn.addEventListener('click', async () => {
        if (!courseId) return;
        try {
          const res = await fetch(`/api/courses/${courseId}/complete`, { method: 'POST' });
          const d = await res.json();
          if (res.ok) {
            showAlert(d.message || 'Kursus ditandai selesai. Tugas otomatis ditambahkan.', 'success');
            await loadCoursesFromServer();
            await loadAssignments();
            await refreshProgressFromServer();
          } else {
            showAlert(d.message || 'Gagal menandai selesai', 'error');
          }
        } catch (err) {
          console.error(err);
          showAlert('Gagal menghubungi server', 'error');
        }
      });
    }
  });
}

async function openResourceModal(title, type, url) {
  const modal = document.getElementById('resource-modal');
  const modalTitle = document.getElementById('resource-modal-title');
  const modalBody = document.getElementById('resource-modal-body');
  const modalType = document.getElementById('resource-modal-type');

  modalTitle.textContent = title;
  modalType.textContent = type === 'video' ? 'Video Pembelajaran' : 'E-book Materi';
  modalBody.innerHTML = '';

  if (!url) {
    modalBody.innerHTML = '<p>Link materi tidak tersedia.</p>';
  } else if (type === 'video') {
    const videoId = extractYouTubeId(url);
    if (videoId) {
      modalBody.innerHTML = `<iframe src="https://www.youtube.com/embed/${videoId}" frameborder="0" allowfullscreen></iframe>`;
    } else {
      modalBody.innerHTML = `<div class="resource-link"><a href="${url}" target="_blank" rel="noopener noreferrer">Buka Video di tab baru</a></div>`;
    }
  } else {
    modalBody.innerHTML = `<iframe src="${url}" frameborder="0"></iframe>`;
  }

  modal.classList.remove('hidden');
}

function closeResourceModal() {
  const modal = document.getElementById('resource-modal');
  if (modal) modal.classList.add('hidden');
}

function extractYouTubeId(url) {
  const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]+)/;
  const match = url.match(regex);
  return match ? match[1] : '';
}

function updateProgressFromTasks() {
  // removed in-memory task state; progress now comes from backend refresh
}

// Fetch courses from backend and render; fallback to local sample
async function loadCoursesFromServer() {
  try {
    const res = await fetch('/api/courses');
    if (res.ok) {
      const courses = await res.json();
      if (courses && courses.length) {
        courseList.length = 0;
        courseList.push(...courses);
        renderCourseLibrary(courses);
        initializeCourseActions();
        return;
      }
    }
  } catch (err) {
    console.error('Load courses error:', err);
  }

  // fallback to built-in sample
  renderCourseLibrary(courseLibraryData);
  initializeCourseActions();
}

function setupAddCourseButton() {
  const btn = document.getElementById('new-resource-btn');
  if (!btn) return;
  const modal = document.getElementById('course-add-modal');
  const closeModalBtn = document.getElementById('close-course-add-modal');
  const form = document.getElementById('course-add-form');

  btn.addEventListener('click', () => {
    if (modal) modal.classList.remove('hidden');
  });

  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const title = form.title.value.trim();
      const type = form.type.value;
      const author = form.author.value.trim();
      const duration = form.duration.value.trim();
      const description = form.description.value.trim();
      const resource_url = form.resource_url.value.trim();

      if (!title || !resource_url) {
        showAlert('Judul dan link materi wajib diisi', 'error');
        return;
      }

      try {
        const res = await fetch('/api/courses', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, type, author, duration, description, resource_url })
        });
        if (res.status === 201) {
          showAlert('Kursus berhasil dibuat', 'success');
          modal.classList.add('hidden');
          form.reset();
          await loadCoursesFromServer();
          await refreshProgressFromServer();
        } else {
          const d = await res.json();
          showAlert(d.message || 'Gagal membuat kursus', 'error');
        }
      } catch (err) {
        console.error('Create course error', err);
        showAlert('Gagal membuat kursus', 'error');
      }
    });
  }
}

async function loadAssignments() {
  try {
    const res = await fetch('/api/assignments');
    if (!res.ok) return;
    const items = await res.json();
    renderAssignments(items);
    setupAssignmentActions();
  } catch (err) {
    console.error('Load assignments error', err);
  }
}

function renderAssignments(items) {
  const pendingEl = document.getElementById('pending-assignments-list');
  const completedEl = document.getElementById('completed-assignments-list');
  const pendingCountEl = document.getElementById('pending-count');
  const completedCountEl = document.getElementById('completed-count');

  if (!pendingEl || !completedEl) return;

  const pendingItems = items.filter(a => !a.completed);
  const completedItems = items.filter(a => a.completed);

  pendingCountEl.textContent = `(${pendingItems.length})`;
  completedCountEl.textContent = `(${completedItems.length})`;

  pendingEl.innerHTML = pendingItems.length
    ? pendingItems.map(renderAssignmentCard).join('')
    : '<p class="empty-state">Tidak ada tugas aktif saat ini.</p>';

  completedEl.innerHTML = completedItems.length
    ? completedItems.map(renderAssignmentCard).join('')
    : '<p class="empty-state">Riwayat masih kosong. Selesaikan tugas untuk melihatnya di sini.</p>';
}

function renderAssignmentCard(a) {
  const actionButton = a.completed
    ? `<button class="btn-secondary repeat-assignment-btn assignment-button">Kerjakan Kembali</button>`
    : `<button class="btn-primary complete-assignment-btn assignment-button">Selesaikan</button>`;

  return `
    <div class="assignment-item card ${a.completed ? 'assignment-completed' : ''}" data-assign-id="${a.id}">
      <div class="assignment-meta">
        <div>
          <div class="assignment-title">${a.title}</div>
          <div class="assignment-course">${a.course_title || 'Kursus tanpa judul'}</div>
        </div>
        <div>
          <span class="assignment-status">${a.completed ? 'Selesai' : 'Tertunda'}</span>
        </div>
      </div>
      <div class="assignment-actions">
        ${actionButton}
      </div>
    </div>
  `;
}

function setupAssignmentActions() {
  const completeButtons = document.querySelectorAll('.complete-assignment-btn');
  completeButtons.forEach(b => {
    b.addEventListener('click', async (e) => {
      const card = e.target.closest('[data-assign-id]');
      if (!card) return;
      const id = card.dataset.assignId;
      await openAssignmentModal(id, false);
    });
  });

  const repeatButtons = document.querySelectorAll('.repeat-assignment-btn');
  repeatButtons.forEach(b => {
    b.addEventListener('click', async (e) => {
      const card = e.target.closest('[data-assign-id]');
      if (!card) return;
      const id = card.dataset.assignId;
      try {
        const resetRes = await fetch(`/api/assignments/${id}/reset`, { method: 'POST' });
        if (resetRes.ok) {
          showAlert('Tugas siap dikerjakan kembali', 'success');
          await loadAssignments();
          await refreshProgressFromServer();
          await openAssignmentModal(id, false);
        } else {
          showAlert('Gagal mengulangi tugas', 'error');
        }
      } catch (err) {
        console.error(err);
        showAlert('Gagal menghubungi server', 'error');
      }
    });
  });
}

async function openAssignmentModal(assignmentId, isRepeat) {
  try {
    const res = await fetch(`/api/assignments/${assignmentId}/questions`);
    if (!res.ok) {
      showAlert('Gagal memuat soal tugas', 'error');
      return;
    }

    const data = await res.json();
    const titleEl = document.getElementById('assignment-modal-title');
    const courseEl = document.getElementById('assignment-modal-course');
    const bodyEl = document.getElementById('assignment-modal-body');
    const actionsEl = document.getElementById('assignment-modal-actions');

    if (!titleEl || !courseEl || !bodyEl || !actionsEl) return;

    titleEl.textContent = data.assignment.title;
    courseEl.textContent = `Kursus: ${data.course_title}`;

    bodyEl.innerHTML = `
      <div class="assignment-questions">
        ${data.questions.map((q, index) => `<div class="assignment-question"><strong>Soal ${index + 1}</strong><p>${q}</p></div>`).join('')}
      </div>
    `;

    actionsEl.innerHTML = `
      <button class="btn-secondary" onclick="closeAssignmentModal()">Tutup</button>
      ${!data.assignment.completed ? '<button class="btn-primary" id="assignment-modal-complete-btn">Selesaikan</button>' : '<button class="btn-primary" id="assignment-modal-repeat-btn">Selesai Lagi</button>'}
    `;

    const modal = document.getElementById('assignment-modal');
    if (modal) modal.classList.remove('hidden');

    if (!data.assignment.completed) {
      const completeBtn = document.getElementById('assignment-modal-complete-btn');
      if (completeBtn) {
        completeBtn.addEventListener('click', async () => {
          const completeRes = await fetch(`/api/assignments/${assignmentId}/complete`, { method: 'POST' });
          if (completeRes.ok) {
            showAlert('Tugas selesai dan masuk riwayat', 'success');
            closeAssignmentModal();
            await loadCoursesFromServer();
            await loadAssignments();
            await refreshProgressFromServer();
          } else {
            showAlert('Gagal menyelesaikan tugas', 'error');
          }
        });
      }
    } else {
      const repeatBtn = document.getElementById('assignment-modal-repeat-btn');
      if (repeatBtn) {
        repeatBtn.addEventListener('click', () => {
          showAlert('Latihan ulang dimulai', 'success');
        });
      }
    }
  } catch (err) {
    console.error('Assignment modal error', err);
    showAlert('Gagal memuat tugas', 'error');
  }
}

function closeAssignmentModal() {
  const modal = document.getElementById('assignment-modal');
  if (modal) modal.classList.add('hidden');
}

// Refresh progress by combining baseProgress + assignments + in-memory course tasks
async function refreshProgressFromServer() {
  try {
    const res = await fetch('/api/assignments');
    let assignments = [];
    if (res.ok) assignments = await res.json();

    const totalAssign = assignments.length;
    const completedAssign = assignments.filter(a => a.completed).length;

    const base = window.__baseProgress || { completed: 0, inProgress: 0, notStarted: 0 };
    const merged = {
      completed: base.completed + completedAssign,
      inProgress: base.inProgress + Math.max(0, totalAssign - completedAssign),
      notStarted: Math.max(0, base.notStarted)
    };

    renderDonut(merged);
    renderLegend(merged);
  } catch (err) {
    console.error('refresh progress error', err);
  }
}

function filterCourses(type) {
  const cards = document.querySelectorAll('.course-library-card');
  cards.forEach(card => {
    const cardType = card.dataset.type;
    card.style.display = type === 'all' || cardType === type ? 'flex' : 'none';
  });
}

function closeCourseAddModal() {
  const modal = document.getElementById('course-add-modal');
  if (modal) modal.classList.add('hidden');
}

function renderDonut(progress) {
  const svg = document.getElementById("donut-chart");
  const total = progress.completed + progress.inProgress + progress.notStarted;
  document.getElementById("donut-total").textContent = total;

  const cx = 80;
  const cy = 80;
  const r = 62;
  const strokeWidth = 16;
  const circumference = 2 * Math.PI * r;
  let offsetAccum = 0;

  const segments = [
    { value: progress.completed, color: "var(--done)" },
    { value: progress.inProgress, color: "var(--inprogress)" },
    { value: progress.notStarted, color: "var(--notstarted)" },
  ];

  svg.innerHTML = "";
  svg.innerHTML += `
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
      style="stroke:#F0F1F8; stroke-width:${strokeWidth};"
    />
  `;

  if (total === 0) {
    return;
  }

  segments.forEach(seg => {
    const fraction = seg.value / total;
    const dash = fraction * circumference;
    svg.innerHTML += `
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
        style="stroke:${seg.color}; stroke-width:${strokeWidth}; stroke-linecap:round;"
        stroke-dasharray="${dash} ${circumference}"
        stroke-dashoffset="${offsetAccum}"
        transform="rotate(-90 ${cx} ${cy})"
      />
    `;
    offsetAccum += dash;
  });
}

function renderLegend(progress) {
  const el = document.getElementById("legend-list");
  const total = progress.completed + progress.inProgress + progress.notStarted;
  const items = [
    { label: "Selesai", value: progress.completed, color: "var(--done)" },
    { label: "Berjalan", value: progress.inProgress, color: "var(--inprogress)" },
    { label: "Belum Mulai", value: progress.notStarted, color: "var(--notstarted)" },
  ];
  el.innerHTML = items.map(i => `
    <li>
      <span class="dot" style="background:${i.color}"></span>
      <span class="legend-label">${i.label}</span>
      <span class="legend-val">${i.value}/${total}</span>
    </li>
  `).join("");
}

function renderTasks(tasks) {
  const el = document.getElementById("task-list");
  el.innerHTML = tasks.map(t => `
    <li class="task-item">
      <div class="task-icon">${t.icon}</div>
      <div>
        <div class="task-title">${t.title}</div>
        <div class="task-time">${t.remaining}</div>
      </div>
    </li>
  `).join("");
}

// Setup logout button
function setupLogoutButton() {
  const logoutItems = document.querySelectorAll('[data-page="logout"]');
  logoutItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  });
}

function applyRoleVisibility() {
  const adminMenu = document.getElementById('admin-panel-menu');
  if (!adminMenu) return;
  const isAdmin = String(window.currentUserRole || 'user').toLowerCase() === 'admin';
  adminMenu.classList.toggle('hidden', !isAdmin);

  const adminButtons = document.querySelectorAll('.add-task-btn, .complete-course-btn, .complete-task-btn, #new-resource-btn, #admin-open-course-modal');
  adminButtons.forEach(button => {
    if (button && button.dataset.roleLocked !== 'always') {
      button.style.display = isAdmin ? '' : 'none';
    }
  });
}

async function loadAdminUsers() {
  if (String(window.currentUserRole || 'user').toLowerCase() !== 'admin') return;

  try {
    const res = await fetch('/api/admin/users');
    if (!res.ok) return;
    const users = await res.json();
    const container = document.getElementById('admin-users-list');
    if (!container) return;
    container.innerHTML = users.map(user => `
      <div class="admin-user-row">
        <div>
          <strong>${user.name}</strong>
          <div class="admin-user-meta">${user.email} • ID: ${user.id} • ${user.is_verified ? 'Terverifikasi' : 'Belum Verifikasi'}</div>
          <div class="admin-user-meta">Kode: ${user.verification_code || 'Belum ada'}</div>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
          <button class="admin-role-btn" data-user-id="${user.id}" data-role="${user.role === 'admin' ? 'user' : 'admin'}">
            ${user.role === 'admin' ? 'Jadikan User' : 'Jadikan Admin'}
          </button>
          <button class="admin-role-btn" data-verify-user-id="${user.id}">
            ${user.is_verified ? 'Reset Kode' : 'Beri Kode'}
          </button>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.admin-role-btn[data-user-id]').forEach(button => {
      button.addEventListener('click', async () => {
        const userId = button.dataset.userId;
        const role = button.dataset.role;
        const response = await fetch(`/api/admin/users/${userId}/role`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role })
        });
        if (response.ok) {
          await loadAdminUsers();
        }
      });
    });

    container.querySelectorAll('.admin-role-btn[data-verify-user-id]').forEach(button => {
      button.addEventListener('click', async () => {
        const userId = button.dataset.verifyUserId;
        const suggestedCode = `ADM-${Math.floor(1000 + Math.random() * 9000)}`;
        const code = window.prompt('Masukkan kode verifikasi untuk user ini', suggestedCode);
        if (code === null) return;
        const trimmedCode = code.trim();
        if (!trimmedCode) {
          alert('Kode verifikasi tidak boleh kosong');
          return;
        }
        const response = await fetch(`/api/admin/users/${userId}/verify`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ verification_code: trimmedCode.toUpperCase(), is_verified: true })
        });
        if (response.ok) {
          await loadAdminUsers();
        }
      });
    });
  } catch (error) {
    console.error('Load admin users error:', error);
  }
}

function setupPageNavigation() {
  const items = document.querySelectorAll('.menu-item[data-page]');
  items.forEach(item => {
    item.addEventListener('click', async (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      if (page === 'logout') return;
      items.forEach(i => i.classList.toggle('active', i === item));
      showPage(page);
      if (page === 'assignment') {
        await loadAssignments();
      }
      if (page === 'events') {
        renderEvents(eventData);
      }
      if (page === 'settings') {
        await loadSettings();
      }
      if (page === 'admin-panel') {
        await loadAdminUsers();
      }
    });
  });
}

function showPage(page) {
  const dashboardPage = document.getElementById('dashboard-page');
  const coursesPage = document.getElementById('courses-page');
  const assignmentsPage = document.getElementById('assignments-page');
  const eventsPage = document.getElementById('events-page');
  const settingsPage = document.getElementById('settings-page');
  const adminPage = document.getElementById('admin-panel-page');

  dashboardPage.classList.toggle('hidden', page !== 'dashboard');
  coursesPage.classList.toggle('hidden', page !== 'courses');
  if (assignmentsPage) assignmentsPage.classList.toggle('hidden', page !== 'assignment');
  if (eventsPage) eventsPage.classList.toggle('hidden', page !== 'events');
  if (settingsPage) settingsPage.classList.toggle('hidden', page !== 'settings');
  if (adminPage) adminPage.classList.toggle('hidden', page !== 'admin-panel');
}

function getNotificationIcon(type) {
  if (type === 'tugas') return '📝';
  if (type === 'pesan') return '💬';
  if (type === 'event') return '📅';
  return '🔔';
}

function formatRelativeTime(dateString) {
  if (!dateString) return 'baru saja';
  const diffMs = Date.now() - new Date(dateString).getTime();
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000));

  if (diffMinutes < 1) return 'baru saja';
  if (diffMinutes < 60) return `${diffMinutes} menit lalu`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} jam lalu`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays} hari lalu`;

  return new Date(dateString).toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
}

function renderNotifications(items = []) {
  const notificationList = document.getElementById('notification-list');
  const notificationBadge = document.getElementById('notification-badge');
  if (!notificationList || !notificationBadge) return;

  const unreadCount = items.filter(item => !item.is_read).length;
  notificationBadge.textContent = unreadCount;
  notificationBadge.classList.toggle('hidden', unreadCount === 0);

  if (!items.length) {
    notificationList.innerHTML = '<div class="notification-empty">Tidak ada notifikasi.</div>';
    return;
  }

  notificationList.innerHTML = items.map(item => `
    <div class="notification-item ${item.is_read ? '' : 'unread'}" data-notification-id="${item.id}" data-type="${item.type || 'general'}">
      <div class="notification-icon">${getNotificationIcon(item.type)}</div>
      <div class="notification-content">
        <div class="notification-title">${item.title || 'Notifikasi'}</div>
        <div class="notification-message">${item.message || ''}</div>
        <div class="notification-time">${formatRelativeTime(item.created_at)}</div>
      </div>
    </div>
  `).join('');

  notificationList.querySelectorAll('.notification-item').forEach(item => {
    item.addEventListener('click', async () => {
      const id = item.dataset.notificationId;
      const type = item.dataset.type;
      await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
      await loadNotifications();

      if (type === 'tugas') {
        showPage('assignment');
        await loadAssignments();
      }
    });
  });
}

async function loadNotifications() {
  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) {
      renderNotifications([]);
      return;
    }
    const notifications = await res.json();
    renderNotifications(notifications);
  } catch (error) {
    console.error('Load notifications error:', error);
    renderNotifications([]);
  }
}

async function markAllNotificationsRead() {
  try {
    await fetch('/api/notifications/read-all', { method: 'POST' });
    await loadNotifications();
  } catch (error) {
    console.error('Mark all notifications read error:', error);
  }
}

async function initNotificationBell() {
  const button = document.getElementById('notification-btn');
  const panel = document.getElementById('notification-panel');
  const markAllReadBtn = document.getElementById('mark-all-read-btn');

  if (!button || !panel) return;

  button.addEventListener('click', async () => {
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
      await loadNotifications();
    }
  });

  if (markAllReadBtn) {
    markAllReadBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      await markAllNotificationsRead();
    });
  }

  document.addEventListener('click', (event) => {
    if (!panel.contains(event.target) && !button.contains(event.target)) {
      panel.classList.add('hidden');
    }
  });

  await loadNotifications();
}

window.chatState = {
  conversations: [],
  currentConversationId: null,
  pollingId: null,
  users: []
};

function getChatDisplayName(conversation) {
  if (conversation.display_name) return conversation.display_name;
  if (conversation.name) return conversation.name;
  if (conversation.type === 'group') return 'Grup';
  return 'Chat baru';
}

async function loadUsersForChat() {
  try {
    const res = await fetch('/api/users');
    if (!res.ok) return;
    window.chatState.users = await res.json();
    const list = document.getElementById('chat-user-list');
    if (list) renderChatUserOptions();
  } catch (error) {
    console.error('Load chat users error:', error);
  }
}

function renderChatUserOptions() {
  const list = document.getElementById('chat-user-list');
  if (!list) return;
  if (!window.chatState.users.length) {
    list.innerHTML = '<div class="empty-chat">Belum ada pengguna lain.</div>';
    return;
  }

  list.innerHTML = window.chatState.users.map(user => `
    <label class="chat-user-item">
      <input type="checkbox" name="member_ids" value="${user.id}" />
      <span>
        ${user.name || user.email}
        <small style="display:block;color:var(--text-gray);font-size:11px;margin-top:2px;">ID: ${user.id}</small>
      </span>
    </label>
  `).join('');
}

async function loadConversations() {
  try {
    const res = await fetch('/api/conversations');
    if (!res.ok) return;
    const conversations = await res.json();
    window.chatState.conversations = conversations || [];

    const list = document.getElementById('conversation-list');
    if (!list) return;

    if (!conversations.length) {
      list.innerHTML = '<div class="empty-chat">Belum ada percakapan.</div>';
      return;
    }

    list.innerHTML = conversations.map(conversation => `
      <button class="conversation-item ${String(conversation.id) === String(window.chatState.currentConversationId) ? 'active' : ''}" data-conversation-id="${conversation.id}" type="button">
        <div class="conversation-name">${getChatDisplayName(conversation)}</div>
        <div class="conversation-preview">${conversation.last_message || 'Belum ada pesan'}</div>
      </button>
    `).join('');

    list.querySelectorAll('.conversation-item').forEach(button => {
      button.addEventListener('click', async () => {
        const id = button.dataset.conversationId;
        await openConversation(id);
      });
    });

    if (!window.chatState.currentConversationId && conversations.length) {
      await openConversation(conversations[0].id);
    }
  } catch (error) {
    console.error('Load conversations error:', error);
  }
}

async function openConversation(conversationId) {
  window.chatState.currentConversationId = conversationId;
  const list = document.getElementById('conversation-list');
  if (list) {
    list.querySelectorAll('.conversation-item').forEach(button => {
      button.classList.toggle('active', String(button.dataset.conversationId) === String(conversationId));
    });
  }

  await loadMessages(conversationId);
}

async function loadMessages(conversationId) {
  try {
    const res = await fetch(`/api/conversations/${conversationId}/messages`);
    if (!res.ok) {
      const header = document.getElementById('thread-header');
      if (header) header.textContent = 'Percakapan tidak tersedia';
      return;
    }

    const data = await res.json();
    const conversation = window.chatState.conversations.find(item => String(item.id) === String(conversationId));
    const header = document.getElementById('thread-header');
    if (header) {
      header.textContent = conversation ? getChatDisplayName(conversation) : 'Percakapan';
    }

    const thread = document.getElementById('thread-messages');
    if (!thread) return;

    const messages = data.messages || [];
    if (!messages.length) {
      thread.innerHTML = '<div class="empty-chat">Mulai percakapan dengan mengirim pesan pertama.</div>';
      return;
    }

    thread.innerHTML = messages.map(msg => `
      <div class="message-bubble ${Number(msg.sender_id) === Number(window.currentUserId) ? 'mine' : 'other'}">
        <div>${msg.content}</div>
        <span class="message-meta">${msg.sender_name || 'Pengirim'} • ${formatRelativeTime(msg.created_at)}</span>
      </div>
    `).join('');

    thread.scrollTop = thread.scrollHeight;
  } catch (error) {
    console.error('Load messages error:', error);
  }
}

async function initMessagePanel() {
  const button = document.getElementById('messages-btn');
  const panel = document.getElementById('messages-panel');
  const form = document.getElementById('message-form');
  const newChatBtn = document.getElementById('new-chat-btn');
  const modal = document.getElementById('chat-create-modal');

  if (!button || !panel) return;

  button.addEventListener('click', async () => {
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
      await loadUsersForChat();
      await loadConversations();
    }
  });

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content || !window.chatState.currentConversationId) return;

    try {
      const res = await fetch(`/api/conversations/${window.chatState.currentConversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });
      const data = await res.json();
      if (!res.ok) {
        showAlert(data.message || 'Gagal mengirim pesan', 'error');
        return;
      }
      input.value = '';
      await loadMessages(window.chatState.currentConversationId);
      await loadConversations();
    } catch (error) {
      console.error('Send message error:', error);
      showAlert('Gagal mengirim pesan', 'error');
    }
  });

  newChatBtn?.addEventListener('click', async () => {
    await loadUsersForChat();
    renderChatUserOptions();
    if (modal) modal.classList.remove('hidden');
  });

  document.addEventListener('click', (event) => {
    if (!panel.contains(event.target) && !button.contains(event.target)) {
      panel.classList.add('hidden');
    }
  });

  document.getElementById('chat-create-close')?.addEventListener('click', () => {
    document.getElementById('chat-create-modal')?.classList.add('hidden');
  });

  const chatForm = document.getElementById('chat-create-form');
  chatForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const type = document.getElementById('chat-type').value;
    const name = document.getElementById('chat-group-name').value.trim();
    const selected = [...document.querySelectorAll('input[name="member_ids"]:checked')].map(item => Number(item.value));

    if (type === 'private' && selected.length !== 1) {
      showAlert('Pilih satu pengguna untuk chat pribadi', 'error');
      return;
    }

    if (type === 'group' && (!name || selected.length < 2)) {
      showAlert('Nama grup dan minimal 2 anggota wajib diisi', 'error');
      return;
    }

    try {
      const res = await fetch('/api/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type,
          name,
          member_ids: selected
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showAlert(data.message || 'Gagal membuat percakapan', 'error');
        return;
      }

      document.getElementById('chat-create-modal')?.classList.add('hidden');
      chatForm.reset();
      await loadConversations();
      if (data.conversation?.id) {
        await openConversation(data.conversation.id);
      }
    } catch (error) {
      console.error('Create conversation error:', error);
      showAlert('Gagal membuat percakapan', 'error');
    }
  });

  const chatType = document.getElementById('chat-type');
  const groupNameWrap = document.getElementById('chat-group-name-wrap');
  chatType?.addEventListener('change', () => {
    const isGroup = chatType.value === 'group';
    if (groupNameWrap) groupNameWrap.classList.toggle('hidden', !isGroup);
  });

  if (window.chatState.pollingId) clearInterval(window.chatState.pollingId);
  window.chatState.pollingId = setInterval(async () => {
    if (document.getElementById('messages-panel') && !document.getElementById('messages-panel').classList.contains('hidden')) {
      await loadConversations();
      if (window.chatState.currentConversationId) {
        await loadMessages(window.chatState.currentConversationId);
      }
    }
  }, 4000);

  await loadUsersForChat();
  await loadConversations();
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    if (!res.ok) {
      if (res.status === 401) {
        window.location.href = '/login';
      }
      return;
    }

    const data = await res.json();
    const profileForm = document.getElementById('settings-profile-form');
    const passwordForm = document.getElementById('settings-password-form');
    const notificationForm = document.getElementById('settings-notifications-form');

    if (profileForm) {
      profileForm.elements.name.value = data.profile?.name || '';
      profileForm.elements.email.value = data.profile?.email || '';
      profileForm.elements.avatar_url.value = data.profile?.avatar_url || '';
    }

    if (notificationForm) {
      notificationForm.elements.assignments.checked = Boolean(data.settings?.assignments !== false);
      notificationForm.elements.messages.checked = Boolean(data.settings?.messages !== false);
      notificationForm.elements.events.checked = Boolean(data.settings?.events !== false);
      notificationForm.elements.dark_mode.checked = Boolean(data.settings?.dark_mode);
    }

    if (passwordForm) {
      passwordForm.reset();
    }

    const userNameEl = document.querySelector('.user-name');
    if (userNameEl && data.user?.name) {
      userNameEl.textContent = data.user.name;
    }

    const welcomeTitle = document.getElementById('welcome-title');
    if (welcomeTitle && data.user?.name) {
      welcomeTitle.textContent = `Selamat datang kembali, ${data.user.name}!`;
    }
  } catch (err) {
    console.error('Load settings error:', err);
  }
}

function setupSettingsForms() {
  const profileForm = document.getElementById('settings-profile-form');
  if (profileForm) {
    profileForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        name: profileForm.elements.name.value.trim(),
        email: profileForm.elements.email.value.trim(),
        avatar_url: profileForm.elements.avatar_url.value.trim()
      };

      try {
        const res = await fetch('/api/settings/profile', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          showAlert(data.message || 'Gagal memperbarui profil', 'error');
          return;
        }
        showAlert(data.message || 'Profil berhasil diperbarui', 'success');
        await loadSettings();
      } catch (err) {
        console.error('Update profile error:', err);
        showAlert('Gagal memperbarui profil', 'error');
      }
    });
  }

  const passwordForm = document.getElementById('settings-password-form');
  if (passwordForm) {
    passwordForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        old_password: passwordForm.elements.old_password.value,
        new_password: passwordForm.elements.new_password.value,
        confirm_password: passwordForm.elements.confirm_password.value
      };

      try {
        const res = await fetch('/api/settings/password', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          showAlert(data.message || 'Gagal mengubah password', 'error');
          return;
        }
        showAlert(data.message || 'Password berhasil diperbarui', 'success');
        passwordForm.reset();
      } catch (err) {
        console.error('Update password error:', err);
        showAlert('Gagal mengubah password', 'error');
      }
    });
  }

  const notificationsForm = document.getElementById('settings-notifications-form');
  if (notificationsForm) {
    notificationsForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const payload = {
        assignments: notificationsForm.elements.assignments.checked,
        messages: notificationsForm.elements.messages.checked,
        events: notificationsForm.elements.events.checked,
        dark_mode: notificationsForm.elements.dark_mode.checked
      };

      try {
        const res = await fetch('/api/settings/notifications', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) {
          showAlert(data.message || 'Gagal menyimpan preferensi', 'error');
          return;
        }
        showAlert(data.message || 'Preferensi berhasil disimpan', 'success');
      } catch (err) {
        console.error('Update notifications error:', err);
        showAlert('Gagal menyimpan preferensi', 'error');
      }
    });
  }
}

function setupCourseFilter() {
  const buttons = document.querySelectorAll('.filter-pill');
  buttons.forEach(button => {
    button.addEventListener('click', () => {
      buttons.forEach(btn => btn.classList.remove('active'));
      button.classList.add('active');
      filterCourses(button.dataset.filter);
    });
  });
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  const isAuthenticated = await checkAuth();
  if (isAuthenticated) {
    applyRoleVisibility();
    loadDashboard();
    setupLogoutButton();
    setupPageNavigation();
    setupCourseFilter();
    setupSettingsForms();
    initNotificationBell();
    initMessagePanel();
    if (String(window.currentUserRole || 'user').toLowerCase() === 'admin') {
      await loadAdminUsers();
    }
  }
});
