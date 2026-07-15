"use client";

/**
 * ChatInput — Message composition area with auto-growing textarea.
 *
 * Supports Enter to send, Shift+Enter for newlines, and disabled
 * state while the assistant is responding.
 */

import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import styles from "./chat-input.module.scss";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="22" />
    </svg>
  );
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Ask about courses, book a room, or get CS help...",
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isMicActive, setIsMicActive] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to force browser to recalculate natural scrollHeight
      textareaRef.current.style.height = "auto";
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [value]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;

        recognitionRef.current.onstart = () => {
          setIsCapturing(true);
        };
        
        recognitionRef.current.onresult = (event: any) => {
          let transcript = "";
          for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
          }
          setValue(transcript);
        };

        recognitionRef.current.onerror = (event: any) => {
          console.error("Speech recognition error", event.error);
          setIsMicActive(false);
          setIsCapturing(false);
        };

        recognitionRef.current.onend = () => {
          setIsMicActive(false);
          setIsCapturing(false);
        };
      }
    }
  }, []);

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isMicActive) {
      recognitionRef.current.stop();
      setIsMicActive(false);
      setIsCapturing(false);
    } else {
      setValue(""); 
      try {
        recognitionRef.current.start();
        setIsMicActive(true);
      } catch (err) {
        console.error("Speech recognition start failed", err);
      }
    }
  }, [isMicActive]);

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (isMicActive) {
        recognitionRef.current?.stop();
        setIsMicActive(false);
        setIsCapturing(false);
      }
      
      const trimmed = value.trim();
      if (!trimmed || disabled) return;
      onSend(trimmed);
      setValue("");
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    },
    [value, disabled, onSend, isMicActive]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e as unknown as FormEvent);
      }
    },
    [handleSubmit]
  );

  return (
    <div className={styles.inputWrapper}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.textareaWrapper}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder={isMicActive ? (isCapturing ? "Listening..." : "Starting...") : placeholder}
            disabled={disabled}
            rows={1}
            id="chat-input"
          />
          <div className={styles.controlsRow}>
            <button
              type="button"
              className={`${styles.iconBtn} ${isMicActive ? styles.activeMic : ""} ${isCapturing ? styles.capturing : ""}`}
              onClick={toggleListening}
              aria-label="Toggle voice input"
              title="Voice input"
            >
              <MicIcon />
            </button>
            <button
              type="submit"
              className={styles.sendBtn}
              disabled={disabled || !value.trim()}
              id="send-message-btn"
              aria-label="Send message"
            >
              <SendIcon />
            </button>
          </div>
        </div>
      </form>
      <div className={styles.hint}>
        Press Enter to send · Shift+Enter for new line
      </div>
    </div>
  );
}
