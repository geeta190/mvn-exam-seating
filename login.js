// Select the username input field
const usernameInput = document.getElementById("username-field");

// Pattern: Username 'MVN' se shuru hoga (Jaise MVN001, MVN123, mvn001)
const usernamePattern = /^MVN\w{3}$/i;

usernameInput.addEventListener("input", () => {
  const username = usernameInput.value;
  if (usernamePattern.test(username)) {
    usernameInput.setCustomValidity("");
  } else {
    usernameInput.setCustomValidity(
      "Username must start with 'MVN' and be followed by 3 characters (e.g. MVN001)"
    );
  }
});

// Select the password input field (Ab koi bhi aasan 6-letter password chalega)
const passwordInput = document.getElementById("password-field");

passwordInput.addEventListener("input", () => {
  const password = passwordInput.value;
  if (password.length >= 6) {
    passwordInput.setCustomValidity("");
  } else {
    passwordInput.setCustomValidity("Password must be at least 6 characters long");
  }
});