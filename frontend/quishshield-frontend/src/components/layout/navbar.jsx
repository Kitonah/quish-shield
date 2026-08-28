import { ShieldCheck } from "lucide-react";

function Navbar() {
  return (
    <nav className="border-b border-white/10 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-pink-500">
            <ShieldCheck size={21} />
          </div>

          <span className="text-xl font-bold tracking-tight">
            Quish<span className="text-purple-400">Shield</span>
          </span>
        </div>

       {/*
       { //Navigation//
        <div className="hidden items-center gap-8 text-sm text-slate-400 md:flex">
          <a href="#" className="transition hover:text-white">
            Scanner
          </a>

          <a href="#" className="transition hover:text-white">
            Cyber Cell
          </a>

          <a href="#" className="transition hover:text-white">
            About
          </a>
        </div>  */}

        {/* Status */}
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
          <span className="h-2 w-2 rounded-full bg-green-400" />
          System Online
        </div>

      </div>
    </nav>
  );
}

export default Navbar;