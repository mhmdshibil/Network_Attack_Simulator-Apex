import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

const ParticleBackground = () => {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const particleSystemsRef = useRef([]);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });
  const timeRef = useRef(0);
  const rafRef = useRef(null);

  useEffect(() => {
    // Detect mobile/touch devices
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
                     ('ontouchstart' in window);
    
    if (isMobile) {
      return;
    }

    const container = containerRef.current;
    const width = window.innerWidth;
    const height = window.innerHeight;

    // Scene setup
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Camera setup (orthographic for 2D-like effect)
    const camera = new THREE.OrthographicCamera(
      width / -2, width / 2,
      height / 2, height / -2,
      1, 1000
    );
    camera.position.z = 500;
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Vertex shader
    const vertexShader = `
      uniform float time;
      uniform vec2 mouse;
      uniform float clusterPhase;
      uniform vec2 clusterCenter;
      uniform float rotationSpeed;
      
      attribute vec3 offset;
      attribute float angle;
      attribute float speed;
      attribute vec3 color;
      attribute float size;
      
      varying vec3 vColor;
      varying float vAlpha;
      
      void main() {
        vColor = color;
        
        // Calculate rotation influence based on mouse
        vec2 mouseInfluence = mouse * 0.3;
        float rotationAngle = time * rotationSpeed + clusterPhase + 
                              length(mouseInfluence) * 0.5;
        
        // Rotate particle position
        float cos_r = cos(rotationAngle + angle);
        float sin_r = sin(rotationAngle + angle);
        
        vec3 rotated = vec3(
          offset.x * cos_r - offset.y * sin_r,
          offset.x * sin_r + offset.y * cos_r,
          offset.z
        );
        
        // Add wave motion
        float wave = sin(time * speed + angle * 2.0) * 15.0;
        rotated.x += wave;
        rotated.y += cos(time * speed + angle) * 15.0;
        
        // Mouse interaction - pull particles slightly toward mouse
        vec2 toMouse = mouseInfluence * 50.0;
        rotated.xy += toMouse * (1.0 - length(offset.xy) / 300.0) * 0.3;
        
        // Apply cluster center
        vec3 finalPosition = rotated + vec3(clusterCenter, 0.0);
        
        vec4 mvPosition = modelViewMatrix * vec4(finalPosition, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        
        // Size and alpha based on depth and distance
        float distanceFromCenter = length(offset.xy) / 300.0;
        gl_PointSize = size * (1.0 - distanceFromCenter * 0.3) * (300.0 / -mvPosition.z);
        
        vAlpha = 0.6 + sin(time * speed * 2.0) * 0.3;
        vAlpha *= (1.0 - distanceFromCenter * 0.5);
      }
    `;

    // Fragment shader
    const fragmentShader = `
      varying vec3 vColor;
      varying float vAlpha;
      
      void main() {
        // Create dash/line shape
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        
        // Elongated dash shape
        float dashShape = 1.0 - smoothstep(0.0, 0.5, abs(center.x) * 2.0);
        dashShape *= 1.0 - smoothstep(0.0, 0.3, abs(center.y) * 4.0);
        
        float alpha = dashShape * vAlpha;
        
        if (alpha < 0.01) discard;
        
        gl_FragColor = vec4(vColor, alpha);
      }
    `;

    // Color palette
    const colors = [
      new THREE.Color(0x4A90E2), // Blue
      new THREE.Color(0x7B68EE), // Purple
      new THREE.Color(0x50C878), // Emerald
      new THREE.Color(0xF4A460), // Sandy brown / yellow
      new THREE.Color(0xFF6B9D), // Pink
      new THREE.Color(0x00CED1), // Turquoise
    ];

    // Create multiple particle clusters
    const clusterCount = 6;
    const particlesPerCluster = 300;

    for (let c = 0; c < clusterCount; c++) {
      const geometry = new THREE.BufferGeometry();
      
      const positions = [];
      const offsets = [];
      const angles = [];
      const speeds = [];
      const particleColors = [];
      const sizes = [];

      // Create radial burst pattern
      for (let i = 0; i < particlesPerCluster; i++) {
        positions.push(0, 0, 0);
        
        // Radial distribution
        const radius = Math.pow(Math.random(), 0.7) * 280 + 20;
        const theta = Math.random() * Math.PI * 2;
        
        offsets.push(
          Math.cos(theta) * radius,
          Math.sin(theta) * radius,
          (Math.random() - 0.5) * 50
        );
        
        angles.push(theta);
        speeds.push(0.5 + Math.random() * 1.0);
        
        // Assign color from palette
        const color = colors[Math.floor(Math.random() * colors.length)];
        particleColors.push(color.r, color.g, color.b);
        
        sizes.push(3 + Math.random() * 4);
      }

      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute('offset', new THREE.Float32BufferAttribute(offsets, 3));
      geometry.setAttribute('angle', new THREE.Float32BufferAttribute(angles, 1));
      geometry.setAttribute('speed', new THREE.Float32BufferAttribute(speeds, 1));
      geometry.setAttribute('color', new THREE.Float32BufferAttribute(particleColors, 3));
      geometry.setAttribute('size', new THREE.Float32BufferAttribute(sizes, 1));

      // Position clusters across the screen
      const cols = 3;
      const rows = 2;
      const col = c % cols;
      const row = Math.floor(c / cols);
      
      const clusterX = (col - (cols - 1) / 2) * (width / (cols + 0.5));
      const clusterY = (row - (rows - 1) / 2) * (height / (rows + 0.5));

      const material = new THREE.ShaderMaterial({
        uniforms: {
          time: { value: 0 },
          mouse: { value: new THREE.Vector2(0, 0) },
          clusterPhase: { value: (c / clusterCount) * Math.PI * 2 },
          clusterCenter: { value: new THREE.Vector2(clusterX, clusterY) },
          rotationSpeed: { value: 0.1 + Math.random() * 0.1 }
        },
        vertexShader,
        fragmentShader,
        transparent: true,
        depthTest: false,
        depthWrite: false,
        blending: THREE.AdditiveBlending
      });

      const particles = new THREE.Points(geometry, material);
      scene.add(particles);
      particleSystemsRef.current.push(particles);
    }

    // Mouse move handler
    const handleMouseMove = (event) => {
      mouseRef.current.targetX = (event.clientX / width) * 2 - 1;
      mouseRef.current.targetY = -(event.clientY / height) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Animation loop
    const animate = () => {
      rafRef.current = requestAnimationFrame(animate);
      
      timeRef.current += 0.01;
      
      // Smooth mouse interpolation
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;
      
      // Update all particle systems
      particleSystemsRef.current.forEach((particles) => {
        particles.material.uniforms.time.value = timeRef.current;
        particles.material.uniforms.mouse.value.set(
          mouseRef.current.x,
          mouseRef.current.y
        );
      });
      
      renderer.render(scene, camera);
    };

    animate();

    // Resize handler
    const handleResize = () => {
      const newWidth = window.innerWidth;
      const newHeight = window.innerHeight;
      
      camera.left = newWidth / -2;
      camera.right = newWidth / 2;
      camera.top = newHeight / 2;
      camera.bottom = newHeight / -2;
      camera.updateProjectionMatrix();
      
      renderer.setSize(newWidth, newHeight);
      
      // Reposition clusters
      const cols = 3;
      const rows = 2;
      particleSystemsRef.current.forEach((particles, index) => {
        const col = index % cols;
        const row = Math.floor(index / cols);
        const clusterX = (col - (cols - 1) / 2) * (newWidth / (cols + 0.5));
        const clusterY = (row - (rows - 1) / 2) * (newHeight / (rows + 0.5));
        particles.material.uniforms.clusterCenter.value.set(clusterX, clusterY);
      });
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
      }
      
      particleSystemsRef.current.forEach((particles) => {
        particles.geometry.dispose();
        particles.material.dispose();
        scene.remove(particles);
      });
      
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        background: 'transparent'
      }}
    />
  );
};

export default ParticleBackground;
