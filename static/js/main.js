document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.querySelector(".app-sidebar");
  const toggle = document.querySelector(".menu-toggle");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (window.innerWidth <= 960 && sidebar.classList.contains("open")) {
        if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
          sidebar.classList.remove("open");
        }
      }
    });
  }

  const darkToggle = document.querySelector("#darkModeToggle");
  const body = document.body;
  if (localStorage.getItem("erp-dark-mode") === "1") {
    body.classList.add("dark-mode");
  }
  if (darkToggle) {
    darkToggle.addEventListener("click", () => {
      body.classList.toggle("dark-mode");
      localStorage.setItem("erp-dark-mode", body.classList.contains("dark-mode") ? "1" : "0");
    });
  }

  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("submit", (e) => {
      if (!confirm(el.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });

  // Auto-dismiss flash messages
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity .4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // ---------- Generic Login Page ----------

  // Show/hide password toggle for generic login
  const toggleLoginPassword = document.getElementById("toggleLoginPassword");
  const loginPassword = document.getElementById("loginPassword");

  if (toggleLoginPassword && loginPassword) {
    toggleLoginPassword.addEventListener("click", () => {
      const type = loginPassword.type === "password" ? "text" : "password";
      loginPassword.type = type;
      const icon = toggleLoginPassword.querySelector("i");
      icon.classList.toggle("fa-eye");
      icon.classList.toggle("fa-eye-slash");
    });
  }

  // Generic login form validation
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      const username = loginForm.querySelector('input[name="username"]');
      const password = loginForm.querySelector('input[name="password"]');

      if (!username.value.trim() || !password.value) {
        e.preventDefault();
        if (!username.value.trim()) {
          username.focus();
        } else {
          password.focus();
        }
        return;
      }

      // Show loading state
      const loginBtn = document.getElementById("loginBtn");
      const btnText = loginBtn.querySelector(".btn-text");
      const btnLoader = loginBtn.querySelector(".btn-loader");

      loginBtn.disabled = true;
      btnText.style.display = "none";
      btnLoader.style.display = "flex";
    });
  }

  // ---------- Student Login Page ----------

  // Show/hide password toggle
  const togglePassword = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("password");

  if (togglePassword && passwordInput) {
    togglePassword.addEventListener("click", () => {
      const type = passwordInput.type === "password" ? "text" : "password";
      passwordInput.type = type;
      const icon = togglePassword.querySelector("i");
      icon.classList.toggle("fa-eye");
      icon.classList.toggle("fa-eye-slash");
    });
  }

  // Show/hide confirm password toggle (reset password page)
  const toggleConfirmPassword = document.getElementById("toggleConfirmPassword");
  const confirmPasswordInput = document.getElementById("confirm_password");

  if (toggleConfirmPassword && confirmPasswordInput) {
    toggleConfirmPassword.addEventListener("click", () => {
      const type = confirmPasswordInput.type === "password" ? "text" : "password";
      confirmPasswordInput.type = type;
      const icon = toggleConfirmPassword.querySelector("i");
      icon.classList.toggle("fa-eye");
      icon.classList.toggle("fa-eye-slash");
    });
  }

  // Student login form validation
  const studentLoginForm = document.getElementById("studentLoginForm");
  if (studentLoginForm) {
    studentLoginForm.addEventListener("submit", (e) => {
      let isValid = true;

      const studentId = document.getElementById("student_id");
      const password = document.getElementById("password");
      const studentIdError = document.getElementById("studentIdError");
      const passwordError = document.getElementById("passwordError");

      // Reset errors
      studentIdError.textContent = "";
      passwordError.textContent = "";
      studentId.classList.remove("error");
      password.classList.remove("error");

      // Validate student ID
      if (!studentId.value.trim()) {
        studentIdError.textContent = "Please enter your Student ID.";
        studentId.classList.add("error");
        isValid = false;
      }

      // Validate password
      if (!password.value) {
        passwordError.textContent = "Please enter your password.";
        password.classList.add("error");
        isValid = false;
      }

      if (!isValid) {
        e.preventDefault();
        return;
      }

      // Show loading state
      const loginBtn = document.getElementById("loginBtn");
      const btnText = loginBtn.querySelector(".btn-text");
      const btnLoader = loginBtn.querySelector(".btn-loader");

      loginBtn.disabled = true;
      btnText.style.display = "none";
      btnLoader.style.display = "flex";
    });
  }

  // Forgot password form validation
  const forgotPasswordForm = document.getElementById("forgotPasswordForm");
  if (forgotPasswordForm) {
    forgotPasswordForm.addEventListener("submit", (e) => {
      let isValid = true;

      const studentId = document.getElementById("student_id");
      const studentIdError = document.getElementById("studentIdError");

      // Reset errors
      studentIdError.textContent = "";
      studentId.classList.remove("error");

      // Validate student ID
      if (!studentId.value.trim()) {
        studentIdError.textContent = "Please enter your Student ID.";
        studentId.classList.add("error");
        isValid = false;
      }

      if (!isValid) {
        e.preventDefault();
        return;
      }

      // Show loading state
      const submitBtn = document.getElementById("submitBtn");
      const btnText = submitBtn.querySelector(".btn-text");
      const btnLoader = submitBtn.querySelector(".btn-loader");

      submitBtn.disabled = true;
      btnText.style.display = "none";
      btnLoader.style.display = "flex";
    });
  }

  // Reset password form validation
  const resetPasswordForm = document.getElementById("resetPasswordForm");
  if (resetPasswordForm) {
    resetPasswordForm.addEventListener("submit", (e) => {
      let isValid = true;

      const password = document.getElementById("password");
      const confirmPassword = document.getElementById("confirm_password");
      const passwordError = document.getElementById("passwordError");
      const confirmPasswordError = document.getElementById("confirmPasswordError");

      // Reset errors
      passwordError.textContent = "";
      confirmPasswordError.textContent = "";
      password.classList.remove("error");
      confirmPassword.classList.remove("error");

      // Validate password
      if (!password.value) {
        passwordError.textContent = "Please enter your password.";
        password.classList.add("error");
        isValid = false;
      } else if (password.value.length < 8) {
        passwordError.textContent = "Password must be at least 8 characters.";
        password.classList.add("error");
        isValid = false;
      }

      // Validate confirm password
      if (!confirmPassword.value) {
        confirmPasswordError.textContent = "Please confirm your password.";
        confirmPassword.classList.add("error");
        isValid = false;
      } else if (password.value !== confirmPassword.value) {
        confirmPasswordError.textContent = "Passwords do not match.";
        confirmPassword.classList.add("error");
        isValid = false;
      }

      if (!isValid) {
        e.preventDefault();
        return;
      }

      // Show loading state
      const submitBtn = document.getElementById("submitBtn");
      const btnText = submitBtn.querySelector(".btn-text");
      const btnLoader = submitBtn.querySelector(".btn-loader");

      submitBtn.disabled = true;
      btnText.style.display = "none";
      btnLoader.style.display = "flex";
    });
  }

  // ---------- Toast Notification System ----------
  window.showToast = function(message, type = 'info') {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
      success: 'fa-check-circle',
      danger: 'fa-exclamation-circle',
      warning: 'fa-exclamation-triangle',
      info: 'fa-info-circle'
    };

    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('hiding');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  };

  // ---------- Modal System ----------
  window.openModal = function(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) overlay.classList.add('active');
  };

  window.closeModal = function(modalId) {
    const overlay = document.getElementById(modalId);
    if (overlay) overlay.classList.remove('active');
  };

  // Close modal on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('active');
    });
  });

  // Close modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach(o => o.classList.remove('active'));
    }
  });

  // ---------- Chart.js Initialization ----------
  window.initChart = function(canvasId, type, data, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    if (typeof Chart === 'undefined') return null;

    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 16, usePointStyle: true }
        }
      }
    };

    return new Chart(canvas, {
      type: type,
      data: data,
      options: { ...defaultOptions, ...options }
    });
  };

  // ---------- AJAX Helper ----------
  window.ajaxRequest = async function(url, method = 'GET', data = null) {
    const options = {
      method: method,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    };
    if (data && method !== 'GET') {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(data);
    }
    try {
      const response = await fetch(url, options);
      return await response.json();
    } catch (error) {
      console.error('AJAX Error:', error);
      return { success: false, message: 'Request failed' };
    }
  };

  // ---------- Search & Filter ----------
  document.querySelectorAll('[data-search-target]').forEach(searchInput => {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase();
      const targetSelector = e.target.getAttribute('data-search-target');
      document.querySelectorAll(targetSelector).forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(query) ? '' : 'none';
      });
    });
  });

  // ---------- Confirmation Dialogs ----------
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', (e) => {
      if (!confirm(el.getAttribute('data-confirm'))) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });
});
