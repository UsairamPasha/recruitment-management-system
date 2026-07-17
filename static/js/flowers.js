const flowerContainer = document.getElementById('flower-background');
const flowerCount = 40; // Number of flowers

for (let i = 0; i < flowerCount; i++) {
    const flower = document.createElement('span');
    flower.className = 'flower';
    flower.innerText = '🌸';

    // Random position
    flower.style.top = Math.random() * 100 + '%';
    flower.style.left = Math.random() * 100 + '%';

    // Random size between 1rem and 3rem
    const size = 1 + Math.random() * 2;
    flower.style.fontSize = `${size}rem`;

    // Optional: random rotation
    const rotation = Math.random() * 360;
    flower.style.transform = `rotate(${rotation}deg)`;

    flowerContainer.appendChild(flower);
}
