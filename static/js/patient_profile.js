
document.addEventListener("DOMContentLoaded", () => {
    const dobInput = document.getElementById("date_of_birth");
    const ageInput = document.getElementById("age");

    const heightInput = document.getElementById("height_cm");
    const weightInput = document.getElementById("weight_kg");
    const bmiInput = document.getElementById("bmi");

    const form = document.getElementById("patientProfileForm");

    // Calculate age from date of birth.
    function calculateAge() {
        if (!dobInput || !ageInput) return;

        const dobValue = dobInput.value;

        if (!dobValue) {
            ageInput.value = "";
            return;
        }

        const dob = new Date(`${dobValue}T00:00:00`);
        const today = new Date();

        if (Number.isNaN(dob.getTime()) || dob > today) {
            ageInput.value = "";
            return;
        }

        let age = today.getFullYear() - dob.getFullYear();

        const birthdayNotReached =
            today.getMonth() < dob.getMonth() ||
            (
                today.getMonth() === dob.getMonth() &&
                today.getDate() < dob.getDate()
            );

        if (birthdayNotReached) {
            age--;
        }

        ageInput.value = `${age} years`;
    }

    // Calculate BMI from height in centimetres and weight in kilograms.
    function calculateBMI() {
        if (!heightInput || !weightInput || !bmiInput) return;

        const height = Number(heightInput.value);
        const weight = Number(weightInput.value);

        if (
            heightInput.value.trim() === "" ||
            weightInput.value.trim() === "" ||
            !Number.isFinite(height) ||
            !Number.isFinite(weight) ||
            height <= 0 ||
            weight <= 0
        ) {
            bmiInput.value = "";
            return;
        }

        const heightMetres = height / 100;
        const bmi = weight / (heightMetres * heightMetres);

        bmiInput.value = bmi.toFixed(1);
    }

    if (dobInput) {
        dobInput.addEventListener("change", calculateAge);
        calculateAge();
    }

    if (heightInput) {
        heightInput.addEventListener("input", calculateBMI);
    }

    if (weightInput) {
        weightInput.addEventListener("input", calculateBMI);
    }

    calculateBMI();

    // Avoid submitting an impossible future date of birth.
    if (form && dobInput) {
        form.addEventListener("submit", (event) => {
            if (!dobInput.value) return;

            const dob = new Date(`${dobInput.value}T00:00:00`);
            const today = new Date();
            today.setHours(23, 59, 59, 999);

            if (Number.isNaN(dob.getTime()) || dob > today) {
                event.preventDefault();
                dobInput.setCustomValidity(
                    "Date of birth cannot be in the future."
                );
                dobInput.reportValidity();
            } else {
                dobInput.setCustomValidity("");
            }
        });

        dobInput.addEventListener("input", () => {
            dobInput.setCustomValidity("");
        });
    }

    // Restore calculated fields after Reset Changes is clicked.
    if (form) {
        form.addEventListener("reset", () => {
            setTimeout(() => {
                calculateAge();
                calculateBMI();
            }, 0);
        });
    }
});
