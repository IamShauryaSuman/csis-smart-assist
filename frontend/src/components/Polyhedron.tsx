"use client";

import React, { useEffect, useRef, useState } from "react";

const φ = (1 + Math.sqrt(5)) / 2;

// Icosahedron vertices
const icoVertices: [number, number, number][] = [
    [-1, φ, 0], [1, φ, 0], [-1, -φ, 0], [1, -φ, 0],
    [0, -1, φ], [0, 1, φ], [0, -1, -φ], [0, 1, -φ],
    [φ, 0, -1], [φ, 0, 1], [-φ, 0, -1], [-φ, 0, 1]
].map(([x, y, z]) => {
    const len = Math.sqrt(x * x + y * y + z * z);
    return [x / len, y / len, z / len] as [number, number, number];
});

// Icosahedron faces (indices of vertices)
const icoFaces = [
    [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
    [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
    [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
    [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
];

// Function to subdivide faces for Geodesic Sphere
const getGeodesicSphere = (frequency: number) => {
    let vertices = [...icoVertices];
    let faces = [...icoFaces];

    for (let f = 0; f < frequency - 1; f++) {
        const newFaces: number[][] = [];
        const midpoints = new Map<string, number>();

        const getMidpoint = (i1: number, i2: number) => {
            const key = [i1, i2].sort().join("-");
            if (midpoints.has(key)) return midpoints.get(key)!;

            const v1 = vertices[i1];
            const v2 = vertices[i2];
            const mid: [number, number, number] = [
                (v1[0] + v2[0]) / 2,
                (v1[1] + v2[1]) / 2,
                (v1[2] + v2[2]) / 2
            ];
            // Project to sphere
            const len = Math.sqrt(mid[0] ** 2 + mid[1] ** 2 + mid[2] ** 2);
            vertices.push([mid[0] / len, mid[1] / len, mid[2] / len]);
            const index = vertices.length - 1;
            midpoints.set(key, index);
            return index;
        };

        faces.forEach(([a, b, c]) => {
            const ab = getMidpoint(a, b);
            const bc = getMidpoint(b, c);
            const ca = getMidpoint(c, a);

            newFaces.push([a, ab, ca]);
            newFaces.push([b, bc, ab]);
            newFaces.push([c, ca, bc]);
            newFaces.push([ab, bc, ca]);
        });
        faces = newFaces;
    }

    // Extract edges
    const edgesSet = new Set<string>();
    faces.forEach(([a, b, c]) => {
        [[a, b], [b, c], [c, a]].forEach(([v1, v2]) => {
            edgesSet.add([v1, v2].sort().join("-"));
        });
    });

    const edges = Array.from(edgesSet).map(s => s.split("-").map(Number));
    return { vertices, edges };
};

// Frequency 3 matches the detailed look in the user's image
const { vertices: sphereVertices, edges: sphereEdges } = getGeodesicSphere(3);

export const Polyhedron = () => {
    const [rotation, setRotation] = useState({ x: 0, y: 0 });

    useEffect(() => {
        let frameId: number;
        const animate = () => {
            setRotation(prev => ({
                x: prev.x + 0.0015,
                y: prev.y + 0.002
            }));
            frameId = requestAnimationFrame(animate);
        };
        frameId = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(frameId);
    }, []);

    const project = (v: [number, number, number]) => {
        // Rotation
        let { x, y, z } = { x: v[0], y: v[1], z: v[2] };

        // Rotate Y
        const cosY = Math.cos(rotation.y);
        const sinY = Math.sin(rotation.y);
        const nx = x * cosY - z * sinY;
        const nz1 = x * sinY + z * cosY;
        x = nx;

        // Rotate X
        const cosX = Math.cos(rotation.x);
        const sinX = Math.sin(rotation.x);
        const ny = y * cosX - nz1 * sinX;
        const nz2 = y * sinX + nz1 * cosX;
        y = ny;

        // Perspective projection
        const factor = 450 / (nz2 + 5);
        return {
            x: x * factor + 100,
            y: y * factor + 100,
            z: nz2
        };
    };

    const projectedVertices = sphereVertices.map(project);

    return (
        <div className="w-full h-full flex items-center justify-center opacity-30">
            <svg viewBox="0 0 200 200" className="w-[1200px] h-[1200px] max-w-[200vw] max-h-[200vw]">
                <g stroke="white" strokeWidth="0.25" fill="none">
                    {sphereEdges.map(([i1, i2], idx) => {
                        const v1 = projectedVertices[i1];
                        const v2 = projectedVertices[i2];

                        // Opacity gradient based on depth to create 3D feel
                        const opacity = Math.min(1, Math.max(0.02, (v1.z + v2.z + 2) / 4));

                        return (
                            <line
                                key={idx}
                                x1={v1.x}
                                y1={v1.y}
                                x2={v2.x}
                                y2={v2.y}
                                style={{ opacity }}
                            />
                        );
                    })}
                </g>
            </svg>
        </div>
    );
};
