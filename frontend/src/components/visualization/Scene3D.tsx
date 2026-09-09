import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Eye, EyeOff, RotateCcw, Crosshair } from 'lucide-react';

interface PointData {
  x: number;
  y: number;
  z: number;
  range: number;
  true_range: number;
  range_error: number;
  intensity?: number;
  detection_probability?: number;
}

interface Scene3DProps {
  targetType?: 'cylinder' | 'box';
  targetDbh?: number; // meters
  targetPosition?: [number, number, number];
  points?: PointData[];
}

export const Scene3D: React.FC<Scene3DProps> = ({
  targetType = 'cylinder',
  targetDbh = 0.10,
  targetPosition = [30, 0, 0.5],
  points = [],
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [showRays, setShowRays] = useState(true);
  const [showPoints, setShowPoints] = useState(true);
  const [showTarget, setShowTarget] = useState(true);
  const [showAxes, setShowAxes] = useState(true);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

  const raysGroupRef = useRef<THREE.Group | null>(null);
  const pointsGroupRef = useRef<THREE.Points | null>(null);
  const targetGroupRef = useRef<THREE.Group | null>(null);
  const axesGroupRef = useRef<THREE.AxesHelper | null>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x090d16);

    // Camera (+X forward, +Y right, +Z up per D001)
    const width = mountRef.current.clientWidth;
    const height = mountRef.current.clientHeight || 450;
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 500);
    cameraRef.current = camera;
    // Position camera slightly offset to view LiDAR at origin and target along +X
    camera.position.set(-10, -25, 15);
    camera.up.set(0, 0, 1); // +Z is UP
    camera.lookAt(targetPosition[0] / 2, targetPosition[1], targetPosition[2]);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mountRef.current.replaceChildren(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);
    const dirLight = new THREE.DirectionalLight(0x06b6d4, 1.2);
    dirLight.position.set(10, 10, 20);
    scene.add(dirLight);

    // Ground Grid
    const grid = new THREE.GridHelper(80, 40, 0x06b6d4, 0x1e293b);
    grid.rotation.x = Math.PI / 2; // Lie in XY plane
    scene.add(grid);

    // Coordinate Axes (+X Red=Forward, +Y Green=Right, +Z Blue=Up)
    const axes = new THREE.AxesHelper(5);
    axesGroupRef.current = axes;
    scene.add(axes);

    // LiDAR Sensor Body (at origin [0,0,1.5])
    const lidarGroup = new THREE.Group();
    const sensorGeo = new THREE.CylinderGeometry(0.15, 0.15, 0.25, 24);
    sensorGeo.rotateX(Math.PI / 2);
    const sensorMat = new THREE.MeshStandardMaterial({ color: 0x06b6d4, metalness: 0.8, roughness: 0.2 });
    const sensorMesh = new THREE.Mesh(sensorGeo, sensorMat);
    sensorMesh.position.set(0, 0, 1.5);
    lidarGroup.add(sensorMesh);
    scene.add(lidarGroup);

    // Target (Cylinder or Box)
    const targetGroup = new THREE.Group();
    targetGroupRef.current = targetGroup;
    if (targetType === 'cylinder') {
      const radius = targetDbh / 2;
      const cylGeo = new THREE.CylinderGeometry(radius, radius, 3.0, 32);
      cylGeo.rotateX(Math.PI / 2);
      const cylMat = new THREE.MeshStandardMaterial({ color: 0x10b981, roughness: 0.7 });
      const cylMesh = new THREE.Mesh(cylGeo, cylMat);
      cylMesh.position.set(targetPosition[0], targetPosition[1], targetPosition[2] + 1.5);
      targetGroup.add(cylMesh);
    } else {
      const boxGeo = new THREE.BoxGeometry(0.5, 0.5, 2.0);
      const boxMat = new THREE.MeshStandardMaterial({ color: 0x6366f1, roughness: 0.5 });
      const boxMesh = new THREE.Mesh(boxGeo, boxMat);
      boxMesh.position.set(targetPosition[0], targetPosition[1], targetPosition[2] + 1.0);
      targetGroup.add(boxMesh);
    }
    scene.add(targetGroup);

    // Simulated Rays
    const raysGroup = new THREE.Group();
    raysGroupRef.current = raysGroup;
    const rayMatHit = new THREE.LineBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.4 });
    const rayMatMiss = new THREE.LineBasicMaterial({ color: 0x475569, transparent: true, opacity: 0.15 });

    // Generate sample fan of candidate rays
    for (let i = -15; i <= 15; i++) {
      const az = (i * 0.008);
      const hit = Math.abs(i) <= 6;
      const targetDist = hit ? targetPosition[0] : 60;
      const endX = targetDist * Math.cos(az);
      const endY = targetDist * Math.sin(az);
      const endZ = targetPosition[2] + (i % 3) * 0.2;

      const pointsGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 1.5),
        new THREE.Vector3(endX, endY, endZ),
      ]);
      const line = new THREE.Line(pointsGeom, hit ? rayMatHit : rayMatMiss);
      raysGroup.add(line);
    }
    scene.add(raysGroup);

    // Point Cloud
    const pointCount = points.length > 0 ? points.length : 120;
    const pointPositions = new Float32Array(pointCount * 3);
    const pointColors = new Float32Array(pointCount * 3);

    for (let i = 0; i < pointCount; i++) {
      let x = targetPosition[0] + (Math.random() - 0.5) * targetDbh * 0.9;
      let y = targetPosition[1] + (Math.random() - 0.5) * targetDbh * 0.9;
      let z = targetPosition[2] + Math.random() * 2.0;

      if (points.length > 0 && points[i]) {
        x = points[i].x;
        y = points[i].y;
        z = points[i].z;
      }

      pointPositions[i * 3] = x;
      pointPositions[i * 3 + 1] = y;
      pointPositions[i * 3 + 2] = z;

      // Color mapping
      pointColors[i * 3] = 0.02; // R
      pointColors[i * 3 + 1] = 0.71; // G
      pointColors[i * 3 + 2] = 0.83; // B
    }

    const pointsGeo = new THREE.BufferGeometry();
    pointsGeo.setAttribute('position', new THREE.BufferAttribute(pointPositions, 3));
    pointsGeo.setAttribute('color', new THREE.BufferAttribute(pointColors, 3));

    const pointsMat = new THREE.PointsMaterial({
      size: 0.15,
      vertexColors: true,
      transparent: true,
      opacity: 0.9,
    });
    const pointCloud = new THREE.Points(pointsGeo, pointsMat);
    pointsGroupRef.current = pointCloud;
    scene.add(pointCloud);

    // Mouse Interaction (Orbiting)
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      const rotSpeed = 0.006;
      camera.position.x -= deltaX * rotSpeed * 2;
      camera.position.y += deltaX * rotSpeed * 2;
      camera.position.z += deltaY * rotSpeed * 2;
      camera.lookAt(targetPosition[0] / 2, targetPosition[1], targetPosition[2]);
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 1.05 : 0.95;
      camera.position.multiplyScalar(zoomFactor);
      camera.lookAt(targetPosition[0] / 2, targetPosition[1], targetPosition[2]);
    };

    const dom = renderer.domElement;
    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    dom.addEventListener('wheel', onWheel);

    // Render loop
    let reqId: number;
    const animate = () => {
      reqId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight || 450;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(reqId);
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      dom.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, [targetType, targetDbh, targetPosition, points]);

  // Layer toggles
  useEffect(() => {
    if (raysGroupRef.current) raysGroupRef.current.visible = showRays;
  }, [showRays]);

  useEffect(() => {
    if (pointsGroupRef.current) pointsGroupRef.current.visible = showPoints;
  }, [showPoints]);

  useEffect(() => {
    if (targetGroupRef.current) targetGroupRef.current.visible = showTarget;
  }, [showTarget]);

  useEffect(() => {
    if (axesGroupRef.current) axesGroupRef.current.visible = showAxes;
  }, [showAxes]);

  const handleResetView = () => {
    if (!cameraRef.current) return;
    cameraRef.current.position.set(-10, -25, 15);
    cameraRef.current.lookAt(targetPosition[0] / 2, targetPosition[1], targetPosition[2]);
  };

  return (
    <div className="glass-panel overflow-hidden relative flex flex-col">
      <div className="p-3 border-b border-white/10 flex items-center justify-between bg-slate-900/60 z-10">
        <div className="flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            3D Scene & Point Cloud Viewer
          </span>
          <span className="badge badge-cyan text-[10px]">Three.js WebGL</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowRays(!showRays)}
            className={`btn-secondary text-xs py-1 px-2.5 ${showRays ? 'text-cyan-300' : 'text-slate-500'}`}
            title="Toggle Laser Rays"
          >
            {showRays ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Rays
          </button>

          <button
            onClick={() => setShowPoints(!showPoints)}
            className={`btn-secondary text-xs py-1 px-2.5 ${showPoints ? 'text-cyan-300' : 'text-slate-500'}`}
            title="Toggle Point Cloud"
          >
            {showPoints ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Points
          </button>

          <button
            onClick={() => setShowTarget(!showTarget)}
            className={`btn-secondary text-xs py-1 px-2.5 ${showTarget ? 'text-cyan-300' : 'text-slate-500'}`}
            title="Toggle Target"
          >
            {showTarget ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Target
          </button>

          <button
            onClick={() => setShowAxes(!showAxes)}
            className={`btn-secondary text-xs py-1 px-2.5 ${showAxes ? 'text-cyan-300' : 'text-slate-500'}`}
            title="Toggle Coordinate Axes"
          >
            {showAxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Axes
          </button>

          <button
            onClick={handleResetView}
            className="btn-secondary text-xs py-1 px-2.5 text-slate-300"
            title="Reset Camera View"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </div>
      </div>

      <div ref={mountRef} className="w-full h-[450px] relative cursor-grab active:cursor-grabbing" />

      <div className="p-2.5 bg-slate-900/90 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
            <span>LiDAR Pose: [0, 0, 1.5]m</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span>Target ({targetType}): DBH {Math.round(targetDbh * 100)}cm @ [{targetPosition.join(', ')}]m</span>
          </div>
        </div>

        <div className="text-slate-400">
          Drag to rotate • Scroll to zoom • Right-handed: <span className="text-rose-400">+X forward</span>, <span className="text-emerald-400">+Y right</span>, <span className="text-blue-400">+Z up</span>
        </div>
      </div>
    </div>
  );
};
