import Link from "next/link";

const links = [
  { href: "/", label: "Desk" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/backtest", label: "Backtest" },
];

export function SiteNav() {
  return (
    <nav className="flex flex-wrap gap-4 justify-center text-sm mb-6">
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className="text-blue-400 hover:text-blue-300 underline-offset-4 hover:underline"
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
