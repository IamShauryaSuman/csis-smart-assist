import React, { useEffect, useState } from "react";
import styles from "./loading-screen.module.scss";

interface LoadingScreenProps {
  message?: string;
}

export default function LoadingScreen({ message = "Loading..." }: LoadingScreenProps) {
  const [delay, setDelay] = useState(0);

  useEffect(() => {
    // Sync animation to wall clock to prevent stutter across route transitions
    const offset = (Date.now() % 1000) / 1000;
    setDelay(-offset);
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.loader}>
        <div 
          className={styles.spinner} 
          style={{ animationDelay: `${delay}s` }}
        ></div>
        <p>{message}</p>
      </div>
    </div>
  );
}
