import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Gauge } from "lucide-react";
import { format, parseISO } from "date-fns";
import { ftpTestStatus, spanLabel, TEST_INTERVAL_WEEKS } from "../lib/ftpTest";
import "./FtpTestCard.css";

const HEADLINE = {
  fresh: "Zwift's FTP is current",
  soon: "A ramp test is coming up",
  due: "A ramp test is due",
  unknown: "No ramp test on record yet",
};

/** The ramp-test cycle at a glance: when the last test was, how far through the six weeks, and when the next is due. */
export default function FtpTestCard({ zftp }) {
  const s = ftpTestStatus(zftp);
  return (
    <div className={`card panel-dark ftp-test ${s.state}`}>
      <Gauge size={34} className="ftp-test-icon" aria-hidden="true" />
      <div className="ftp-test-main">
        <span className="call-label">Ramp test</span>
        <h3 className="ftp-test-title">{HEADLINE[s.state]}</h3>
        {s.state === "unknown" ? (
          <p>Zwift's FTP only changes after a ramp test or a race. Once one is logged, the next due date shows here.</p>
        ) : (
          <>
            <p>
              {s.kind === "test" ? "Last test" : "FTP last changed"} {format(parseISO(s.ref), "MMM d")} ({spanLabel(s.days)} ago).
              {s.state === "due"
                ? ` It was due ${s.dueLabel}: the coach will schedule one on a fresh day.`
                : ` Next due about ${s.dueLabel}, in ${spanLabel(Math.max(0, s.daysLeft))}.`}
            </p>
            <div className="ftp-test-bar" role="img" aria-label={`${s.weeks} of ${TEST_INTERVAL_WEEKS} weeks since the last test`}>
              <i style={{ width: `${s.progress * 100}%` }} />
            </div>
          </>
        )}
      </div>
      <Link to="/metrics#ftp" className="metric-more">Why it matters <ArrowRight size={14} /></Link>
    </div>
  );
}
