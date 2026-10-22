import { useState } from "react";
import { Bot, X } from "lucide-react";
import Chat from "../Chat.jsx";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  return (
    <>
      {open && (
        <div className="widget-panel">
          <div className="widget-head">
            <span className="widget-title"><Bot size={18} /> ISDIC Assistant</span>
            <button className="icon-btn" aria-label="Close" onClick={() => setOpen(false)}><X size={18} /></button>
          </div>
          <Chat compact />
        </div>
      )}
      <button className="widget-fab" aria-label="Open assistant" onClick={() => setOpen(!open)}>
        {open ? <X size={22} /> : <Bot size={24} />}
      </button>
    </>
  );
}
