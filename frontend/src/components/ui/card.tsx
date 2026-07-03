import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ elevated, className = "", children, ...props }: CardProps) {
  const bg = elevated ? "bg-[#eef2f8]" : "bg-[#ffffff]";
  return (
    <div
      className={`rounded-[10px] border border-[#dce1e9] ${bg} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`flex items-center justify-between px-5 py-4 ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className = "", children, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={`text-sm font-medium text-[#1f2a44] ${className}`} {...props}>
      {children}
    </h3>
  );
}

export function CardContent({ className = "", children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`px-5 pb-5 ${className}`} {...props}>
      {children}
    </div>
  );
}
