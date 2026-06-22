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
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
                     ('ontouchstart' in window);
    if (isMobile) return;

    const container = containerRef.current;
    const width = window.innerWidth;
    const height = window.innerHeight;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.OrthographicCamera(width / -2, width / 2, height / 2, height / -2, 1, 1000);
    camera.position.z = 500;
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false, powerPreference: 'low-power' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(1);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

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
        vec2 mouseInfluence = mouse * 0.3;
        float rotationAngle = time * rotationSpeed + clusterPhase + length(mouseInfluence) * 0.5;
        float cos_r = cos(rotationAngle + angle);
        float sin_r = sin(rotationAngle + angle);
        vec3 rotated = vec3(offset.x * cos_r - offset.y * sin_r, offset.x * sin_r + offset.y * cos_r, offset.z);
        float wave = sin(time * speed + angle * 2.0) * 15.0;
        rotated.x += wave;
        rotated.y += cos(time * speed + angle) * 15.0;
        vec2 toMouse = mouseInfluence * 50.0;
        rotated.xy += toMouse * (1.0 - length(offset.xy) / 300.0) * 0.3;
        vec3 finalPosition = rotated + vec3(clusterCenter, 0.0);
        vec4 mvPosition = modelViewMatrix * vec4(finalPosition, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        float distanceFromCenter = length(offset.xy) / 300.0;
        gl_PointSize = size * (1.0 - distanceFromCenter * 0.3) * (300.0 / -mvPosition.z);
        vAlpha = 0.15 + sin(time * speed * 2.0) * 0.08;
        vAlpha *= (1.0 - distanceFromCenter * 0.6);
      }
    `;

    const fragmentShader = `
      varying vec3 vColor;
      varying float vAlpha;
      void main() {
        vec2 center = gl_PointCoord - vec2(0.5);
        float dashShape = 1.0 - smoothstep(0.0, 0.5, abs(center.x) * 2.0);
        dashShape *= 1.0 - smoothstep(0.0, 0.3, abs(center.y) * 4.0);
        float alpha = dashShape * vAlpha;
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(vColor, alpha);
      }
    `;

    /* Cold, dim palette — barely visible on #0A0E14 */
    const colors = [
      new THREE.Color(0x0D2035),
      new THREE.Color(0x0A1A28),
      new THREE.Color(0x0C2030),
      new THREE.Color(0x081825),
      new THREE.Color(0x0B1E30),
      new THREE.Color(0x091620),
    ];

    const clusterCount = 6;
    const particlesPerCluster = 200;

    for (let c = 0; c < clusterCount; c++) {
      const geometry = new THREE.BufferGeometry();
      const positions = [], offsets = [], angles = [], speeds = [], particleColors = [], sizes = [];

      for (let i = 0; i < particlesPerCluster; i++) {
        positions.push(0, 0, 0);
        const radius = Math.pow(Math.random(), 0.7) * 280 + 20;
        const theta = Math.random() * Math.PI * 2;
        offsets.push(Math.cos(theta) * radius, Math.sin(theta) * radius, (Math.random() - 0.5) * 50);
        angles.push(theta);
        speeds.push(0.3 + Math.random() * 0.6);
        const color = colors[Math.floor(Math.random() * colors.length)];
        particleColors.push(color.r, color.g, color.b);
        sizes.push(1.5 + Math.random() * 2);
      }

      geometry.setAttribute('position',  new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute('offset',    new THREE.Float32BufferAttribute(offsets, 3));
      geometry.setAttribute('angle',     new THREE.Float32BufferAttribute(angles, 1));
      geometry.setAttribute('speed',     new THREE.Float32BufferAttribute(speeds, 1));
      geometry.setAttribute('color',     new THREE.Float32BufferAttribute(particleColors, 3));
      geometry.setAttribute('size',      new THREE.Float32BufferAttribute(sizes, 1));

      const cols = 3, rows = 2;
      const col = c % cols, row = Math.floor(c / cols);
      const clusterX = (col - (cols - 1) / 2) * (width / (cols + 0.5));
      const clusterY = (row - (rows - 1) / 2) * (height / (rows + 0.5));

      const material = new THREE.ShaderMaterial({
        uniforms: {
          time: { value: 0 },
          mouse: { value: new THREE.Vector2(0, 0) },
          clusterPhase: { value: (c / clusterCount) * Math.PI * 2 },
          clusterCenter: { value: new THREE.Vector2(clusterX, clusterY) },
          rotationSpeed: { value: 0.05 + Math.random() * 0.05 },
        },
        vertexShader, fragmentShader,
        transparent: true, depthTest: false, depthWrite: false,
        blending: THREE.AdditiveBlending,
      });

      const particles = new THREE.Points(geometry, material);
      scene.add(particles);
      particleSystemsRef.current.push(particles);
    }

    const handleMouseMove = (e) => {
      mouseRef.current.targetX = (e.clientX / width) * 2 - 1;
      mouseRef.current.targetY = -(e.clientY / height) * 2 + 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    const animate = () => {
      rafRef.current = requestAnimationFrame(animate);
      timeRef.current += 0.006;
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.04;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.04;
      particleSystemsRef.current.forEach((p) => {
        p.material.uniforms.time.value = timeRef.current;
        p.material.uniforms.mouse.value.set(mouseRef.current.x, mouseRef.current.y);
      });
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      const w = window.innerWidth, h = window.innerHeight;
      camera.left = w / -2; camera.right = w / 2;
      camera.top = h / 2; camera.bottom = h / -2;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      const cols = 3, rows = 2;
      particleSystemsRef.current.forEach((p, i) => {
        const c = i % cols, r = Math.floor(i / cols);
        p.material.uniforms.clusterCenter.value.set(
          (c - (cols - 1) / 2) * (w / (cols + 0.5)),
          (r - (rows - 1) / 2) * (h / (rows + 0.5))
        );
      });
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      particleSystemsRef.current.forEach((p) => {
        p.geometry.dispose();
        p.material.dispose();
        scene.remove(p);
      });
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0, pointerEvents: 'none' }}
    />
  );
};

export default ParticleBackground;
