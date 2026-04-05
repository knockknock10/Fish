import './style.css'

// Scroll reveal animation logic
const setupRevealAnimations = () => {
  const options = {
    threshold: 0.2
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active')
        // We could also unobserve if we only want it to happen once
        // observer.unobserve(entry.target)
      }
    })
  }, options)

  const revealElements = document.querySelectorAll('.reveal')
  revealElements.forEach(el => observer.observe(el))
}

// Subtle mouse movement parallax for hero background
const setupHeroParallax = () => {
  const hero = document.querySelector('#hero')
  if (!hero) return

  hero.addEventListener('mousemove', (e) => {
    const { clientX, clientY } = e
    const moveX = (clientX - window.innerWidth / 2) * 0.01
    const moveY = (clientY - window.innerHeight / 2) * 0.01
    hero.style.backgroundPosition = `calc(50% + ${moveX}px) calc(50% + ${moveY}px)`
  })
}

// Remote interaction for the Simulation Monitor
window.resetSim = () => {
  fetch('http://localhost:5000/reset')
    .then(r => console.log('[*] Reset requested'))
    .catch(e => console.error('[!] Reset failed', e))
}

const setupMonitorClicks = () => {
  const monitorImg = document.querySelector('.fullscreen-feed')
  if (!monitorImg) return

  monitorImg.addEventListener('click', (e) => {
    const rect = monitorImg.getBoundingClientRect()
    // Calculate click percentage for scaling on the backend
    const x_pct = (e.clientX - rect.left) / rect.width
    const y_pct = (e.clientY - rect.top) / rect.height

    fetch('http://localhost:5000/click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x: x_pct, y: y_pct })
    })
    .catch(e => console.error('[!] Click failed', e))
  })
}

const setupCapacityControl = () => {
  const slider = document.querySelector('#capacity-slider')
  const valLabel = document.querySelector('#capacity-val')
  if (!slider || !valLabel) return

  slider.addEventListener('input', (e) => {
    const val = e.target.value
    valLabel.textContent = val
    
    // Send to backend
    fetch('http://localhost:5000/set_capacity', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capacity: parseInt(val) })
    })
    .catch(e => console.error('[!] Capacity sync failed', e))
  })
}

let currentSlide = 0
let slideInterval

const setupProblemSlider = () => {
  const slides = document.querySelectorAll('.problem-slide')
  if (slides.length === 0) return

  const showSlide = (index) => {
    slides.forEach(s => s.classList.remove('active'))
    currentSlide = (index + slides.length) % slides.length
    slides[currentSlide].classList.add('active')
  }

  // Global nav for HTML onclick (Req #4)
  window.nextSlide = () => {
    showSlide(currentSlide + 1)
    resetAutoSlide()
  }

  window.prevSlide = () => {
    showSlide(currentSlide - 1)
    resetAutoSlide()
  }

  const resetAutoSlide = () => {
    clearInterval(slideInterval)
    startAutoSlide()
  }

  const startAutoSlide = () => {
    slideInterval = setInterval(() => {
      showSlide(currentSlide + 1)
    }, 3000) // 3 seconds (Req #4)
  }

  startAutoSlide()
}

// Initial state for hero
const init = () => {
  setupRevealAnimations()
  setupHeroParallax()
  setupMonitorClicks()
  setupCapacityControl()
  setupProblemSlider()
  
  const hero = document.querySelector('#hero')
  if (hero) hero.classList.add('active')
}

document.addEventListener('DOMContentLoaded', init)

// Fallback if DOMContentLoaded already fired
if (document.readyState === 'interactive' || document.readyState === 'complete') {
  init()
}
