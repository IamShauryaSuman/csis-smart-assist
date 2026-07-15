"use client";

/**
 * ChatBubble — Renders a single chat message with Markdown support.
 *
 * Handles both user and assistant messages with distinct visual styles.
 * Uses react-markdown with remark-gfm for rich content rendering.
 */

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check } from "lucide-react";
import type { Message } from "@/lib/types";
import styles from "./chat-bubble.module.scss";

interface ChatBubbleProps {
  message: Message;
  userInitials?: string;
}

function CodeBlock({ node, className, children, ...props }: any) {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || "");
  const codeString = String(children).replace(/\n$/, "");

  const handleCopy = () => {
    navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!match) {
    return (
      <code className={className} style={{ fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace" }} {...props}>
        {children}
      </code>
    );
  }

  return (
    <div className={styles.codeBlockContainer}>
      <div className={styles.codeBlockHeader}>
        <span>{match[1]}</span>
        <button className={styles.copyButton} onClick={handleCopy} aria-label="Copy code">
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <div className={styles.codeBlockContent}>
        <SyntaxHighlighter
          style={materialDark as any}
          language={match[1]}
          PreTag="div"
          customStyle={{ 
            background: "transparent", 
            padding: 0, 
            margin: 0, 
            overflowX: "visible",
            fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace", 
            fontSize: "0.875rem" 
          }}
          codeTagProps={{ style: { fontFamily: "inherit" } }}
          {...props}
        >
          {codeString}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

export default function ChatBubble({ message, userInitials = "U" }: ChatBubbleProps) {
  const isUser = message.role === "user";
  const timestamp = new Date(message.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className={`${styles.bubble} ${
        isUser ? styles.bubbleUser : styles.bubbleAssistant
      }`}
    >
      <div
        className={`${styles.avatar} ${
          isUser ? styles.avatarUser : styles.avatarAssistant
        }`}
      >
        {isUser ? userInitials : "AI"}
      </div>

      <div
        className={`${styles.content} ${
          isUser ? styles.contentUser : ""
        }`}
      >
        <div
          className={`${styles.messageBody} ${
            isUser ? styles.userBody : styles.assistantBody
          }`}
        >
          {isUser ? (
            <span>{message.content}</span>
          ) : !message.content && !message.interactive_type ? (
            <div className={styles.typingDots}>
              <span />
              <span />
              <span />
            </div>
          ) : (
            <div className={styles.markdown}>
              <ReactMarkdown 
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
                  pre: ({ children }) => <>{children}</>,
                  code: CodeBlock
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
        <div
          className={`${styles.timestamp} ${
            isUser ? styles.timestampUser : ""
          }`}
        >
          {timestamp}
        </div>
      </div>
    </div>
  );
}
