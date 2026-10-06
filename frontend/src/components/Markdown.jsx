import ReactMarkdown from "react-markdown";
import "./Markdown.css";

// Coach replies are markdown; links open in a new tab, raw HTML is not rendered.
function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown
        components={{ a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" /> }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}

export default Markdown;
