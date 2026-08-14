import DisclaimerText from "./DisclaimerText";

// §5.7 disclaimer — must appear on the dashboard (wording may be restyled, not reworded).
export default function DisclaimerFooter() {
  return (
    <footer className="bg-gray-900 px-4 py-2 text-center text-[11px] leading-snug text-gray-300">
      <DisclaimerText />
      <a href="/methods" className="underline hover:text-white">
        Methods &amp; limitations
      </a>
    </footer>
  );
}
