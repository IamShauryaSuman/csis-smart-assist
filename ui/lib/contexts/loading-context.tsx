"use client";

import { createContext, useContext, useState } from "react";
import LoadingScreen from "@/components/layout/loading-screen";

interface LoadingContextType {
  setGlobalLoading: (isLoading: boolean, message?: string) => void;
}

const LoadingContext = createContext<LoadingContextType>({
  setGlobalLoading: () => {},
});

export function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  return (
    <LoadingContext.Provider
      value={{
        setGlobalLoading: (l, m) => {
          setLoading(l);
          if (m) setMessage(m);
        },
      }}
    >
      {children}
      {loading && <LoadingScreen message={message} />}
    </LoadingContext.Provider>
  );
}

export const useGlobalLoading = () => useContext(LoadingContext);
