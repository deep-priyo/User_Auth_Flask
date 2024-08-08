document.addEventListener('mousemove', (event) => {
    const snowflake = document.createElement('div');
    snowflake.className = 'snowflake';
    snowflake.style.width = `${Math.random() * 10 + 5}px`;
    snowflake.style.height = snowflake.style.width;
    snowflake.style.left = `${event.clientX}px`;
    snowflake.style.top = `${event.clientY}px`;
    snowflake.style.animationDuration = `${Math.random() * 3 + 2}s`; // Random duration between 2s and 5s
    snowflake.style.animationDelay = `${Math.random() * 2}s`; // Random delay between 0s and 2s
    document.getElementById('snowflakes').appendChild(snowflake);

    setTimeout(() => {
        snowflake.remove(); // Remove the snowflake after animation
    }, 5000); // Duration should be longer than the animation
});
