import React, { useState, useEffect, useRef } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+';

export default function ScrambleText({ text, speed = 40, delay = 0 }) {
  const [displayText, setDisplayText] = useState('');
  const intervalRef = useRef(null);
  const iterationsRef = useRef(0);

  useEffect(() => {
    const startScramble = () => {
      setDisplayText(text.split('').map(() => CHARS[Math.floor(Math.random() * CHARS.length)]).join(''));
      
      intervalRef.current = setInterval(() => {
        setDisplayText((prev) => 
          text.split('').map((char, index) => {
            if (index < iterationsRef.current) {
              return char;
            }
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          }).join('')
        );

        iterationsRef.current += 1 / 3;

        if (iterationsRef.current >= text.length) {
          clearInterval(intervalRef.current);
          setDisplayText(text);
        }
      }, speed);
    };

    const timeoutId = setTimeout(startScramble, delay);

    return () => {
      clearTimeout(timeoutId);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [text, speed, delay]);

  return <span className="scramble-text">{displayText || ' '}</span>;
}