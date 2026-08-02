// IIT Mandi Semester 3 Timetable App logic
let timetableData = null;
let currentView = 'calendar'; // 'calendar' or 'base'
let currentMonday = getMondayOfCurrentWeek(new Date());

const TIME_SLOTS = [
  "08:00 - 08:50",
  "09:00 - 09:50",
  "10:00 - 10:50",
  "11:00 - 11:50",
  "12:00 - 12:50",
  "14:00 - 17:00"
];

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

// DOM elements
const themeToggleBtn = document.getElementById('themeToggleBtn');
const themeMoonIcon = document.getElementById('themeMoonIcon');
const themeSunIcon = document.getElementById('themeSunIcon');
const adminPanelBtn = document.getElementById('adminPanelBtn');
const adminModal = document.getElementById('adminModal');
const closeAdminModalBtn = document.getElementById('closeAdminModalBtn');

const viewWeeklyCalendarBtn = document.getElementById('viewWeeklyCalendarBtn');
const viewBaseGridBtn = document.getElementById('viewBaseGridBtn');
const dateNavigatorContainer = document.getElementById('dateNavigatorContainer');
const prevWeekBtn = document.getElementById('prevWeekBtn');
const todayBtn = document.getElementById('todayBtn');
const nextWeekBtn = document.getElementById('nextWeekBtn');
const currentWeekLabel = document.getElementById('currentWeekLabel');

const timetableGrid = document.getElementById('timetableGrid');
const courseDetailsList = document.getElementById('courseDetailsList');
const courseCountLabel = document.getElementById('courseCountLabel');
const overridesLogList = document.getElementById('overridesLogList');
const activeOverridesCountLabel = document.getElementById('activeOverridesCountLabel');

// Admin form DOM elements
const modalAlert = document.getElementById('modalAlert');
const authSection = document.getElementById('authSection');
const manageSection = document.getElementById('manageSection');
const ghPat = document.getElementById('ghPat');
const ghRepo = document.getElementById('ghRepo');
const ghBranch = document.getElementById('ghBranch');
const saveAuthBtn = document.getElementById('saveAuthBtn');
const disconnectBtn = document.getElementById('disconnectBtn');
const overrideForm = document.getElementById('overrideForm');
const overrideAction = document.getElementById('overrideAction');
const overrideDate = document.getElementById('overrideDate');
const overrideCourse = document.getElementById('overrideCourse');
const overrideTime = document.getElementById('overrideTime');
const overrideVenue = document.getElementById('overrideVenue');
const overrideNote = document.getElementById('overrideNote');
const timeVenueRow = document.getElementById('timeVenueRow');

// Helper to normalize time slot string for matching
function normalizeTime(timeStr) {
  if (!timeStr) return '';
  // Remove spaces, replace 8:50 with 08:50, etc.
  let normalized = timeStr.replace(/\s+/g, '').replace('8:50', '08:50');
  return normalized;
}

// Helper to find Monday of the week for a given date
function getMondayOfCurrentWeek(d) {
  const date = new Date(d);
  const day = date.getDay();
  // day is 0 (Sun) to 6 (Sat)
  // We want Monday (1).
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  return new Date(date.setDate(diff));
}

// Format date to YYYY-MM-DD
function formatDateISO(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Format date to short readable string, e.g. "Aug 3"
function formatDateShort(date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Initialise Theme
function initTheme() {
  const currentTheme = localStorage.getItem('theme') || 'dark';
  if (currentTheme === 'light') {
    document.body.classList.add('light-theme');
    themeMoonIcon.style.display = 'none';
    themeSunIcon.style.display = 'block';
  } else {
    document.body.classList.remove('light-theme');
    themeMoonIcon.style.display = 'block';
    themeSunIcon.style.display = 'none';
  }
}

themeToggleBtn.addEventListener('click', () => {
  document.body.classList.toggle('light-theme');
  const isLight = document.body.classList.contains('light-theme');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  if (isLight) {
    themeMoonIcon.style.display = 'none';
    themeSunIcon.style.display = 'block';
  } else {
    themeMoonIcon.style.display = 'block';
    themeSunIcon.style.display = 'none';
  }
});

// App Startup
window.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  initAdminAuthForm();
  await loadTimetableData();
  renderApp();
});

// Load the JSON timetable data
async function loadTimetableData() {
  try {
    // Attempt to load local timetable.json (which will serve as the initial database)
    const response = await fetch('timetable.json');
    if (!response.ok) throw new Error('Could not fetch timetable.json');
    timetableData = await response.json();
  } catch (error) {
    console.error('Error loading data:', error);
    showModalAlert('Error loading schedule database. Please refresh.', 'danger');
  }
}

// Render everything on screen
function renderApp() {
  if (!timetableData) return;
  
  // Render views
  if (currentView === 'base') {
    dateNavigatorContainer.style.visibility = 'hidden';
    renderBaseTimetable();
  } else {
    dateNavigatorContainer.style.visibility = 'visible';
    updateDateLabels();
    renderDynamicCalendar();
  }

  renderCourseInventory();
  renderOverridesLog();
  populateCourseDropdown();
}

// Update Monday-Friday date range labels
function updateDateLabels() {
  const mon = new Date(currentMonday);
  const fri = new Date(currentMonday);
  fri.setDate(mon.getDate() + 4);
  
  currentWeekLabel.textContent = `${formatDateShort(mon)} – ${formatDateShort(fri)}, ${mon.getFullYear()}`;
}

// Populate Course Selector in Admin override panel
function populateCourseDropdown() {
  if (!timetableData || !overrideCourse) return;
  
  // Keep original selected if any
  const previousVal = overrideCourse.value;
  overrideCourse.innerHTML = '';
  
  Object.keys(timetableData.courses).sort().forEach(code => {
    const opt = document.createElement('option');
    opt.value = code;
    opt.textContent = `${code} (${timetableData.courses[code].name})`;
    overrideCourse.appendChild(opt);
  });
  
  if (previousVal) overrideCourse.value = previousVal;
}

// RENDER METHOD 1: Base Timetable View (Independent of date)
function renderBaseTimetable() {
  timetableGrid.innerHTML = '';
  
  // Header Row
  const timeHeader = document.createElement('div');
  timeHeader.className = 'grid-header-cell time-header-label';
  timeHeader.textContent = 'Time';
  timetableGrid.appendChild(timeHeader);
  
  WEEKDAYS.forEach(day => {
    const dayHeader = document.createElement('div');
    dayHeader.className = 'grid-header-cell';
    dayHeader.textContent = day;
    timetableGrid.appendChild(dayHeader);
  });

  // Schedule Rows
  TIME_SLOTS.forEach(slot => {
    // Row label
    const timeLabel = document.createElement('div');
    timeLabel.className = 'time-slot-label';
    timeLabel.textContent = slot;
    timetableGrid.appendChild(timeLabel);
    
    // Day cells
    WEEKDAYS.forEach(day => {
      const cell = document.createElement('div');
      cell.className = 'timetable-cell empty-slot';
      
      const daySchedule = timetableData.base_schedule[day] || [];
      const item = daySchedule.find(s => normalizeTime(s.time) === normalizeTime(slot));
      
      if (item) {
        cell.className = 'timetable-cell';
        cell.appendChild(createCourseCard(item.course, item.time, item.type, null, null));
      }
      
      timetableGrid.appendChild(cell);
    });
  });
}

// RENDER METHOD 2: Dynamic Calendar View (Processes Date-specific Overrides)
function renderDynamicCalendar() {
  timetableGrid.innerHTML = '';
  
  // Get Dates of target week
  const weekDates = [];
  const todayStr = formatDateISO(new Date());
  
  for (let i = 0; i < 5; i++) {
    const date = new Date(currentMonday);
    date.setDate(currentMonday.getDate() + i);
    weekDates.push(date);
  }

  // Header Row
  const timeHeader = document.createElement('div');
  timeHeader.className = 'grid-header-cell time-header-label';
  timeHeader.textContent = 'Time';
  timetableGrid.appendChild(timeHeader);
  
  weekDates.forEach((date, index) => {
    const dateStr = formatDateISO(date);
    const isToday = dateStr === todayStr;
    
    const dayHeader = document.createElement('div');
    dayHeader.className = `grid-header-cell ${isToday ? 'today-column' : ''}`;
    
    const dayName = WEEKDAYS[index];
    dayHeader.innerHTML = `
      <div>${dayName}</div>
      <div class="date-sublabel">${formatDateShort(date)}</div>
    `;
    timetableGrid.appendChild(dayHeader);
  });

  // For each time slot, evaluate base schedule + overrides for specific dates
  TIME_SLOTS.forEach(slot => {
    // Row label
    const timeLabel = document.createElement('div');
    timeLabel.className = 'time-slot-label';
    timeLabel.textContent = slot;
    timetableGrid.appendChild(timeLabel);
    
    weekDates.forEach((date, dayIndex) => {
      const dayName = WEEKDAYS[dayIndex];
      const dateStr = formatDateISO(date);
      const cell = document.createElement('div');
      cell.className = 'timetable-cell empty-slot';
      
      // 1. Get base schedule items for this slot
      const dayBaseSchedule = timetableData.base_schedule[dayName] || [];
      const baseItem = dayBaseSchedule.find(s => normalizeTime(s.time) === normalizeTime(slot));
      
      // 2. Fetch all overrides affecting this specific date
      const dayOverrides = (timetableData.overrides || []).filter(o => o.date === dateStr);
      
      // Handle the item grid rendering
      let cellData = null;
      
      if (baseItem) {
        // We have a base class scheduled. Let's see if it's altered.
        const cancelOverride = dayOverrides.find(o => o.course === baseItem.course && o.action === 'CANCEL');
        const rescheduleOverride = dayOverrides.find(o => o.course === baseItem.course && o.action === 'RESCHEDULE');
        const locOverride = dayOverrides.find(o => o.course === baseItem.course && o.action === 'LOCATION_CHANGE');
        
        if (cancelOverride) {
          // Cancelled base class
          cell.className = 'timetable-cell';
          cellData = createCourseCard(baseItem.course, baseItem.time, baseItem.type, 'cancel', cancelOverride);
        } else if (rescheduleOverride) {
          // Original slot of a rescheduled class. Mark it as cancelled in its original slot.
          cell.className = 'timetable-cell';
          cellData = createCourseCard(baseItem.course, baseItem.time, baseItem.type, 'cancel', rescheduleOverride);
        } else if (locOverride) {
          // Location changed class
          cell.className = 'timetable-cell';
          cellData = createCourseCard(baseItem.course, baseItem.time, baseItem.type, 'location', locOverride);
        } else {
          // Base class, no overrides
          cell.className = 'timetable-cell';
          cellData = createCourseCard(baseItem.course, baseItem.time, baseItem.type, null, null);
        }
      }
      
      // 3. Check for any rescheduled class landing *into* this slot on this day, or extra classes
      const incomingReschedules = dayOverrides.filter(o => 
        (o.action === 'RESCHEDULE' || o.action === 'EXTRA') && 
        normalizeTime(o.new_time) === normalizeTime(slot)
      );
      
      if (incomingReschedules.length > 0) {
        cell.className = 'timetable-cell';
        const override = incomingReschedules[0]; // Take first matching override
        const overrideType = override.action === 'RESCHEDULE' ? 'reschedule' : 'extra';
        cellData = createCourseCard(override.course, slot, 'Lecture', overrideType, override);
      }
      
      if (cellData) {
        cell.appendChild(cellData);
      }
      
      timetableGrid.appendChild(cell);
    });
  });
}

// Generate Course Card DOM node
function createCourseCard(courseCode, slotTime, classType, overrideStatus, overrideData) {
  const course = timetableData.courses[courseCode];
  if (!course) return null;
  
  const card = document.createElement('div');
  card.className = `course-card c-${courseCode.replace(/P$/, 'P')}`;
  
  let venue = overrideData && overrideData.new_venue ? overrideData.new_venue : course.venue;
  let instructor = course.instructor;
  let statusClass = '';
  let badgeText = '';
  let tooltipNote = '';
  
  if (overrideStatus === 'cancel') {
    statusClass = 'status-cancel';
    badgeText = 'Cancelled';
    tooltipNote = overrideData.note || 'Class cancelled';
  } else if (overrideStatus === 'reschedule') {
    statusClass = 'status-reschedule';
    badgeText = 'Rescheduled';
    tooltipNote = `New Time: ${overrideData.new_time}. Note: ${overrideData.note}`;
  } else if (overrideStatus === 'extra') {
    statusClass = 'status-extra';
    badgeText = 'Extra Class';
    tooltipNote = overrideData.note || 'Extra class scheduled';
  } else if (overrideStatus === 'location') {
    statusClass = 'status-location';
    badgeText = 'Room Changed';
    tooltipNote = `New Venue: ${venue}. Note: ${overrideData.note}`;
  }
  
  if (statusClass) card.classList.add(statusClass);
  
  card.innerHTML = `
    <div class="course-header">
      <span class="course-code">${courseCode}</span>
      <span class="course-type">${classType}</span>
    </div>
    <div class="course-venue">
      <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
      <span>${venue}</span>
    </div>
    <div class="course-instructor">${instructor}</div>
  `;
  
  if (badgeText) {
    const badge = document.createElement('span');
    badge.className = `override-badge badge-${overrideStatus}`;
    badge.textContent = badgeText;
    card.appendChild(badge);
    
    // Add original time details if rescheduled incoming
    if (overrideStatus === 'reschedule' && overrideData.action === 'RESCHEDULE' && normalizeTime(overrideData.new_time) === normalizeTime(slotTime)) {
      const origTime = document.createElement('div');
      origTime.className = 'override-original-time';
      // Find original base time
      origTime.textContent = `Moved from normal slot`;
      card.appendChild(origTime);
    }
  }
  
  // Set hover tooltip
  if (tooltipNote) {
    card.title = tooltipNote;
  } else {
    card.title = `${course.name}\nInstructor: ${instructor}\nCategory: ${course.category} (${course.credits} Credits)`;
  }
  
  return card;
}

// RENDER Inventory list
function renderCourseInventory() {
  courseDetailsList.innerHTML = '';
  const codes = Object.keys(timetableData.courses);
  courseCountLabel.textContent = `${codes.length} Courses`;
  
  codes.sort().forEach(code => {
    const details = timetableData.courses[code];
    const item = document.createElement('div');
    item.className = 'course-details-item';
    
    item.innerHTML = `
      <div class="course-item-left">
        <span class="course-item-dot c-${code.replace(/P$/, 'P')}"></span>
        <div class="course-item-text">
          <span class="course-item-title">${code}: ${details.name}</span>
          <span class="course-item-subtitle">${details.instructor} • ${details.category} (${details.credits} Credits)</span>
        </div>
      </div>
      <div class="course-item-right">
        <span class="course-item-venue">${details.venue}</span>
        <span class="course-item-slot">${details.slot}</span>
      </div>
    `;
    courseDetailsList.appendChild(item);
  });
}

// RENDER Overrides Logs
function renderOverridesLog() {
  overridesLogList.innerHTML = '';
  const overrides = timetableData.overrides || [];
  
  // Filter only active overrides (upcoming or current week onwards)
  const activeCount = overrides.length;
  activeOverridesCountLabel.textContent = `${activeCount} adjustment${activeCount === 1 ? '' : 's'}`;
  
  if (overrides.length === 0) {
    overridesLogList.innerHTML = '<div style="text-align:center; padding: 1.5rem; color: var(--text-muted); font-size: 0.9rem;">No schedule overrides currently recorded. All classes running on base schedule.</div>';
    return;
  }
  
  // Sort overrides by date descending
  const sorted = [...overrides].sort((a, b) => new Date(b.date) - new Date(a.date));
  
  sorted.forEach(over => {
    const item = document.createElement('div');
    item.className = 'override-item';
    
    let actionLabel = over.action;
    let badgeColor = '';
    
    if (over.action === 'CANCEL') badgeColor = 'var(--accent-red)';
    else if (over.action === 'RESCHEDULE') badgeColor = 'var(--accent-blue)';
    else if (over.action === 'EXTRA') badgeColor = 'var(--accent-green)';
    else if (over.action === 'LOCATION_CHANGE') {
      badgeColor = 'var(--accent-yellow)';
      actionLabel = 'ROOM CHANGE';
    }
    
    const formattedDate = new Date(over.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    
    let detailsStr = '';
    if (over.action === 'RESCHEDULE') {
      detailsStr = `• New Time: ${over.new_time} (${over.new_venue})`;
    } else if (over.action === 'EXTRA') {
      detailsStr = `• Time: ${over.new_time} (${over.new_venue})`;
    } else if (over.action === 'LOCATION_CHANGE') {
      detailsStr = `• Room: ${over.new_venue}`;
    }
    
    item.innerHTML = `
      <div class="override-item-left">
        <div class="override-item-header">
          <span class="override-item-date">${formattedDate}</span>
          <span class="override-item-course">${over.course}</span>
          <span class="override-item-action" style="background-color: ${badgeColor};">${actionLabel}</span>
        </div>
        <div class="override-item-note">"${over.note}" ${detailsStr}</div>
        <div class="override-item-source">Source: ${over.source === 'gmail_sync' ? 'Gmail Auto-Sync' : 'Manual Entry'}</div>
      </div>
      <button class="btn btn-danger delete-override-btn" data-id="${over.id}" title="Remove override">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
      </button>
    `;
    
    overridesLogList.appendChild(item);
  });
  
  // Attach deletion listeners
  document.querySelectorAll('.delete-override-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const btnNode = e.currentTarget;
      const overrideId = btnNode.getAttribute('data-id');
      if (confirm('Are you sure you want to delete this schedule override?')) {
        await deleteOverride(overrideId, btnNode);
      }
    });
  });
}

// Week Navigation Handlers
prevWeekBtn.addEventListener('click', () => {
  currentMonday.setDate(currentMonday.getDate() - 7);
  renderApp();
});

nextWeekBtn.addEventListener('click', () => {
  currentMonday.setDate(currentMonday.getDate() + 7);
  renderApp();
});

todayBtn.addEventListener('click', () => {
  currentMonday = getMondayOfCurrentWeek(new Date());
  renderApp();
});

viewWeeklyCalendarBtn.addEventListener('click', () => {
  currentView = 'calendar';
  viewWeeklyCalendarBtn.classList.add('active');
  viewBaseGridBtn.classList.remove('active');
  renderApp();
});

viewBaseGridBtn.addEventListener('click', () => {
  currentView = 'base';
  viewBaseGridBtn.classList.add('active');
  viewWeeklyCalendarBtn.classList.remove('active');
  renderApp();
});

// Admin Panel Toggle
adminPanelBtn.addEventListener('click', () => {
  adminModal.classList.add('active');
});

closeAdminModalBtn.addEventListener('click', () => {
  adminModal.classList.remove('active');
  hideModalAlert();
});

adminModal.addEventListener('click', (e) => {
  if (e.target === adminModal) {
    adminModal.classList.remove('active');
    hideModalAlert();
  }
});

// Action type handler to hide/show times and venues
overrideAction.addEventListener('change', () => {
  const act = overrideAction.value;
  if (act === 'CANCEL') {
    timeVenueRow.style.display = 'none';
    overrideTime.required = false;
    overrideVenue.required = false;
  } else if (act === 'LOCATION_CHANGE') {
    timeVenueRow.style.display = 'grid';
    overrideTime.style.parent = 'none'; // hide time input container or disable it
    overrideTime.required = false;
    overrideVenue.required = true;
  } else {
    timeVenueRow.style.display = 'grid';
    overrideTime.required = true;
    overrideVenue.required = true;
  }
});

// --- ADMIN & GITHUB ACTIONS INTEGRATION ---

// Credentials local storage keys
const STORAGE_KEYS = {
  PAT: 'tt_gh_pat',
  REPO: 'tt_gh_repo',
  BRANCH: 'tt_gh_branch'
};

function initAdminAuthForm() {
  const patVal = localStorage.getItem(STORAGE_KEYS.PAT);
  const repoVal = localStorage.getItem(STORAGE_KEYS.REPO);
  const branchVal = localStorage.getItem(STORAGE_KEYS.BRANCH) || 'main';

  if (patVal && repoVal) {
    ghPat.value = patVal;
    ghRepo.value = repoVal;
    ghBranch.value = branchVal;
    
    // Switch panels
    authSection.style.display = 'none';
    manageSection.style.display = 'block';
  } else {
    authSection.style.display = 'block';
    manageSection.style.display = 'none';
  }
}

saveAuthBtn.addEventListener('click', () => {
  const pat = ghPat.value.trim();
  const repo = ghRepo.value.trim();
  const branch = ghBranch.value.trim() || 'main';

  if (!pat || !repo) {
    showModalAlert('Please provide both a GitHub PAT and Repository name.', 'warning');
    return;
  }

  // Validate format (owner/repo)
  if (!repo.includes('/')) {
    showModalAlert('Repository must be in format "owner/repo-name" (e.g. janesmith/timetable)', 'warning');
    return;
  }

  localStorage.setItem(STORAGE_KEYS.PAT, pat);
  localStorage.setItem(STORAGE_KEYS.REPO, repo);
  localStorage.setItem(STORAGE_KEYS.BRANCH, branch);

  showModalAlert('GitHub credentials connected successfully!', 'success');
  
  // Transition views
  setTimeout(() => {
    authSection.style.display = 'none';
    manageSection.style.display = 'block';
    hideModalAlert();
  }, 1000);
});

disconnectBtn.addEventListener('click', () => {
  localStorage.removeItem(STORAGE_KEYS.PAT);
  localStorage.removeItem(STORAGE_KEYS.REPO);
  localStorage.removeItem(STORAGE_KEYS.BRANCH);
  
  ghPat.value = '';
  ghRepo.value = '';
  ghBranch.value = 'main';

  authSection.style.display = 'block';
  manageSection.style.display = 'none';
  showModalAlert('Disconnected from GitHub repository.', 'success');
  setTimeout(hideModalAlert, 2000);
});

// Modal alerts helper
function showModalAlert(msg, type) {
  modalAlert.textContent = msg;
  modalAlert.className = `alert-box alert-${type}`;
  modalAlert.style.display = 'block';
  adminModal.querySelector('.modal-box').scrollTop = 0;
}

function hideModalAlert() {
  modalAlert.style.display = 'none';
  modalAlert.textContent = '';
}

// Add Override Form submit
overrideForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const action = overrideAction.value;
  const date = overrideDate.value;
  const course = overrideCourse.value;
  const time = overrideTime.value.trim();
  const venue = overrideVenue.value.trim();
  const note = overrideNote.value.trim();

  // Create override object
  const newOverride = {
    id: Date.now().toString(),
    date: date,
    course: course,
    action: action,
    new_time: (action === 'CANCEL' || action === 'LOCATION_CHANGE') ? null : time,
    new_venue: action === 'CANCEL' ? null : (action === 'LOCATION_CHANGE' ? venue : venue),
    source: 'manual',
    note: note
  };

  // Submit to GitHub
  setLoadingState(true);
  showModalAlert('Fetching current database from GitHub...', 'warning');

  const success = await pushOverrideToGitHub(newOverride);
  setLoadingState(false);

  if (success) {
    showModalAlert('Override committed and pushed successfully! Refreshing UI...', 'success');
    overrideForm.reset();
    
    // Update local state and re-render
    timetableData.overrides.push(newOverride);
    renderApp();
    
    setTimeout(() => {
      adminModal.classList.remove('active');
      hideModalAlert();
    }, 1500);
  }
});

function setLoadingState(isLoading) {
  const submitBtn = document.getElementById('submitOverrideBtn');
  if (isLoading) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Committing Changes...';
  } else {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'Save & Push Override';
  }
}

// GitHub Committer Logic to prevent race conditions
async function fetchLatestFromGitHub() {
  const token = localStorage.getItem(STORAGE_KEYS.PAT);
  const repo = localStorage.getItem(STORAGE_KEYS.REPO);
  const branch = localStorage.getItem(STORAGE_KEYS.BRANCH) || 'main';

  const url = `https://api.github.com/repos/${repo}/contents/timetable.json?ref=${branch}`;

  const response = await fetch(url, {
    headers: {
      'Authorization': `token ${token}`,
      'Accept': 'application/vnd.github.v3+json',
      'Cache-Control': 'no-cache'
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to load repository timetable.json. Status: ${response.status}`);
  }

  const data = await response.json();
  const content = atob(data.content.replace(/\s/g, ''));
  const parsed = JSON.parse(content);

  return {
    sha: data.sha,
    data: parsed
  };
}

async function pushOverrideToGitHub(newOverride) {
  const token = localStorage.getItem(STORAGE_KEYS.PAT);
  const repo = localStorage.getItem(STORAGE_KEYS.REPO);
  const branch = localStorage.getItem(STORAGE_KEYS.BRANCH) || 'main';

  try {
    // 1. Fetch latest SHA and contents to prevent race condition write-locks
    const latest = await fetchLatestFromGitHub();
    const updatedData = latest.data;
    
    // 2. Append the new override
    if (!updatedData.overrides) updatedData.overrides = [];
    updatedData.overrides.push(newOverride);
    updatedData.metadata.last_synced = new Date().toISOString();

    // 3. Write back
    const url = `https://api.github.com/repos/${repo}/contents/timetable.json`;
    const payload = {
      message: `manual_override: add ${newOverride.action} for ${newOverride.course} on ${newOverride.date}`,
      content: btoa(unescape(encodeURIComponent(JSON.stringify(updatedData, null, 2)))),
      sha: latest.sha,
      branch: branch
    };

    const putResponse = await fetch(url, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
      },
      body: JSON.stringify(payload)
    });

    if (!putResponse.ok) {
      const errData = await putResponse.json();
      throw new Error(errData.message || 'Error updating repo file');
    }

    // Update global state with latest fetch
    timetableData = updatedData;
    return true;

  } catch (error) {
    console.error('GitHub API error:', error);
    showModalAlert(`GitHub Sync Failed: ${error.message}`, 'danger');
    return false;
  }
}

// Delete an Override
async function deleteOverride(overrideId, btnNode) {
  const token = localStorage.getItem(STORAGE_KEYS.PAT);
  const repo = localStorage.getItem(STORAGE_KEYS.REPO);
  const branch = localStorage.getItem(STORAGE_KEYS.BRANCH) || 'main';

  if (!token || !repo) {
    alert('Please connect your GitHub repository in the Admin Portal to delete overrides.');
    return;
  }

  btnNode.disabled = true;
  btnNode.style.opacity = '0.5';

  try {
    // 1. Fetch latest data
    const latest = await fetchLatestFromGitHub();
    const updatedData = latest.data;

    // 2. Remove override
    const index = updatedData.overrides.findIndex(o => o.id === overrideId);
    if (index === -1) {
      throw new Error('Override not found in the current remote repository.');
    }
    const removedOverride = updatedData.overrides[index];
    updatedData.overrides.splice(index, 1);
    updatedData.metadata.last_synced = new Date().toISOString();

    // 3. Push commit back
    const url = `https://api.github.com/repos/${repo}/contents/timetable.json`;
    const payload = {
      message: `manual_override: remove override for ${removedOverride.course} on ${removedOverride.date}`,
      content: btoa(unescape(encodeURIComponent(JSON.stringify(updatedData, null, 2)))),
      sha: latest.sha,
      branch: branch
    };

    const putResponse = await fetch(url, {
      method: 'PUT',
      headers: {
        'Authorization': `token ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'application/vnd.github.v3+json'
      },
      body: JSON.stringify(payload)
    });

    if (!putResponse.ok) {
      const errData = await putResponse.json();
      throw new Error(errData.message || 'Error deleting override from repository');
    }

    // Success
    timetableData = updatedData;
    renderApp();
    alert('Override deleted and changes pushed successfully.');

  } catch (error) {
    console.error('Delete override error:', error);
    alert(`Failed to delete override: ${error.message}`);
    btnNode.disabled = false;
    btnNode.style.opacity = '1';
  }
}
