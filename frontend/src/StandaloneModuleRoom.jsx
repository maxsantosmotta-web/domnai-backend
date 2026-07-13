import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import './standalone-module-room.css';

export default function StandaloneModuleRoom({ room, onClose, children }) {
  useEffect(() => {
    document.documentElement.classList.add('domnai-standalone-room-open');
    document.body.classList.add('domnai-standalone-room-open');

    return () => {
      if (!document.querySelector('[data-domnai-profile-room]')) {
        document.documentElement.classList.remove('domnai-standalone-room-open');
        document.body.classList.remove('domnai-standalone-room-open');
      }
    };
  }, []);

  if (!room) return null;

  const showBack = room === 'library' || room === 'trash';

  return createPortal(
    <div
      className={`domnai-standalone-room domnai-standalone-room-${room}`}
      data-domnai-standalone-room={room}
    >
      {showBack ? (
        <button type="button" className="domnai-room-back" onClick={onClose}>
          Voltar
        </button>
      ) : null}
      <div className="domnai-standalone-room-main">
        {children}
      </div>
    </div>,
    document.body,
  );
}
