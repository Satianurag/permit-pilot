import { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "pp-btn-primary",
  secondary: "pp-btn-secondary",
  ghost: "pp-btn-ghost",
  danger: "pp-btn-danger",
};

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return <button type="button" className={cn(variants[variant], className)} {...props} />;
}
