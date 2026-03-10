import * as React from "react"
import { cn } from "@/lib/utils"

interface TabsContextType {
  value: string;
  onChange: (value: string) => void;
}

const TabsContext = React.createContext<TabsContextType>({ value: "", onChange: () => {} });

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  onValueChange: (value: string) => void;
}

function Tabs({ value, onValueChange, className, children, ...props }: TabsProps) {
  return (
    <TabsContext.Provider value={{ value, onChange: onValueChange }}>
      <div className={cn("", className)} {...props}>{children}</div>
    </TabsContext.Provider>
  )
}

const TabsList = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("inline-flex h-10 items-center justify-center rounded-lg bg-gray-100 p-1 text-gray-500 dark:bg-gray-800 dark:text-gray-400", className)} {...props} />
  )
)
TabsList.displayName = "TabsList"

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ className, value, ...props }, ref) => {
    const context = React.useContext(TabsContext);
    const isActive = context.value === value;
    return (
      <button
        ref={ref}
        onClick={() => context.onChange(value)}
        className={cn(
          "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all",
          isActive
            ? "bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-gray-100"
            : "hover:text-gray-900 dark:hover:text-gray-100",
          className
        )}
        {...props}
      />
    )
  }
)
TabsTrigger.displayName = "TabsTrigger"

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ className, value, ...props }, ref) => {
    const context = React.useContext(TabsContext);
    if (context.value !== value) return null;
    return <div ref={ref} className={cn("mt-2", className)} {...props} />
  }
)
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }
