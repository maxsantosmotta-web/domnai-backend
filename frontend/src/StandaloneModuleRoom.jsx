import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import './standalone-module-room.css';

export default function StandaloneModuleRoom({ room, children }) {
  useEffect(() => {
    document.documentElement.classList.add('domnai-standalone-room-open');
    document.body.classList.add('domnai-standalone-room-open');

    return () => {
      if (!document.querySelector('[data-domnai-standalone-room]')) {
        document.documentElement.classList.remove('domnai-standalone-room-open');
        document.body.classList.remove('domnai-standalone-room-open');
      }
    };
  }, []);

  if (!room) return null;

  return createPortal(
    <div
      className={`domnai-standalone-room domnai-standalone-room-${room}`}
      data-domnai-standalone-room={room}
    >
      <div className="domnai-standalone-room-main">
        {children}
      </div>
    </div>,
    document.body,
  );
}
