import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { API_BASE_URL, gymAPI } from "../api/client";
import { exerciseLookupUrl } from "../lib/workouts";
import "./ExerciseCarousel.css";

/**
 * Photos of the movement from the open Free Exercise DB (closest match to the name, so the caption says which),
 * swipeable, with the written steps underneath and the Google link kept as a fallback.
 */
export default function ExerciseCarousel({ name }) {
  const { data } = useQuery({
    queryKey: ["exercise-match", name],
    queryFn: async () => (await gymAPI.match(name)).data.match,
    staleTime: 24 * 60 * 60 * 1000,
    retry: false,
  });
  const track = useRef(null);
  const [page, setPage] = useState(0);
  const [steps, setSteps] = useState(false);
  const images = data?.images || [];

  const go = (delta) => {
    const el = track.current;
    if (el) el.scrollBy({ left: delta * el.clientWidth, behavior: "smooth" });
  };

  return (
    <div className="ex-carousel">
      {images.length > 0 && (
        <>
          <div className="ex-track" ref={track} onScroll={(e) => setPage(Math.round(e.currentTarget.scrollLeft / e.currentTarget.clientWidth))}>
            {images.map((path, i) => (
              <img key={path} src={`${API_BASE_URL}/${path}`} alt={`${data.name}, photo ${i + 1} of ${images.length}`} loading="lazy" />
            ))}
          </div>
          {images.length > 1 && (
            <div className="ex-controls">
              <button onClick={() => go(-1)} disabled={page === 0} aria-label="Previous photo"><ChevronLeft size={20} /></button>
              <span className="ex-dots" aria-hidden="true">
                {images.map((p, i) => <i key={p} className={i === page ? "on" : ""} />)}
              </span>
              <button onClick={() => go(1)} disabled={page >= images.length - 1} aria-label="Next photo"><ChevronRight size={20} /></button>
            </div>
          )}
          <p className="ex-caption">
            Closest match: <strong>{data.name}</strong>{data.muscles?.length ? ` · ${data.muscles.slice(0, 3).join(", ")}` : ""}
          </p>
          {data.steps?.length > 0 && (
            <>
              <button className="ex-steps-toggle" onClick={() => setSteps(!steps)} aria-expanded={steps}>
                <ChevronDown size={16} className={steps ? "open" : ""} /> Step by step
              </button>
              {steps && <ol className="ex-steps">{data.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>}
            </>
          )}
        </>
      )}
      <a className="ex-link" href={exerciseLookupUrl(name)} target="_blank" rel="noopener noreferrer">
        More photos and videos <ExternalLink size={14} />
      </a>
    </div>
  );
}
