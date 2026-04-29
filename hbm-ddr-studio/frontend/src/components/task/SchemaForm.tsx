import { useEffect, useMemo, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import type { TaskDescriptor, FormField } from "@/lib/api";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

function fieldSchema(f: FormField) {
  let s: z.ZodTypeAny;
  switch (f.type) {
    case "number":
      s = z.coerce.number();
      if (f.min !== undefined) s = (s as z.ZodNumber).min(f.min);
      if (f.max !== undefined) s = (s as z.ZodNumber).max(f.max);
      break;
    case "boolean":
      s = z.boolean();
      break;
    case "multiselect":
      s = z.array(z.string());
      break;
    default:
      s = z.string();
      if (f.required) s = (s as z.ZodString).min(1, "required");
  }
  if (!f.required && f.type !== "boolean" && f.type !== "multiselect") s = s.optional();
  return s;
}

export function descriptorToZod(desc: TaskDescriptor) {
  const shape: Record<string, z.ZodTypeAny> = {};
  for (const sec of desc.form.sections) for (const f of sec.fields) shape[f.key] = fieldSchema(f);
  return z.object(shape);
}

function defaultsFor(desc: TaskDescriptor): Record<string, any> {
  const out: Record<string, any> = {};
  for (const sec of desc.form.sections) {
    for (const f of sec.fields) {
      if (f.default !== undefined && f.default !== null) out[f.key] = f.default;
      else if (f.type === "boolean") out[f.key] = false;
      else if (f.type === "multiselect") out[f.key] = [];
      else out[f.key] = "";
    }
  }
  return out;
}

export type SchemaFormHandle = {
  values: Record<string, any>;
  isValid: boolean;
  missingKeys: string[];
};

export function SchemaForm({
  descriptor,
  onChange,
}: {
  descriptor: TaskDescriptor;
  onChange?: (handle: SchemaFormHandle) => void;
}) {
  const schema = useMemo(() => descriptorToZod(descriptor), [descriptor]);
  const defaults = useMemo(() => defaultsFor(descriptor), [descriptor]);
  const { control, watch, formState } = useForm({
    resolver: zodResolver(schema),
    defaultValues: defaults,
    mode: "onChange",
  });
  const values = watch();
  const requiredKeys = useMemo(() => {
    const keys: string[] = [];
    for (const sec of descriptor.form.sections) for (const f of sec.fields) if (f.required) keys.push(f.key);
    return keys;
  }, [descriptor]);
  const missingKeys = requiredKeys.filter((k) => {
    const v = (values as any)[k];
    return v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0);
  });

  useEffect(() => {
    onChange?.({ values, isValid: formState.isValid && missingKeys.length === 0, missingKeys });
  }, [values, formState.isValid, missingKeys.join(","), onChange]); // eslint-disable-line

  return (
    <Accordion type="multiple" defaultValue={descriptor.form.sections.map((_, i) => `s${i}`)}>
      {descriptor.form.sections.map((sec, i) => (
        <AccordionItem key={sec.title} value={`s${i}`} className="border-b border-border last:border-0">
          <AccordionTrigger className="text-sm font-medium">{sec.title}</AccordionTrigger>
          <AccordionContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {sec.fields.map((f) => {
                const err = (formState.errors as any)[f.key];
                const isMissing = missingKeys.includes(f.key);
                return (
                  <div key={f.key} className="space-y-1.5">
                    <Label htmlFor={f.key} className="flex items-center gap-1">
                      {(f.label || f.key)}
                      {f.required && <span className="text-destructive">*</span>}
                    </Label>
                    <Controller
                      name={f.key}
                      control={control}
                      render={({ field }) => {
                        const cls = cn(isMissing && "border-destructive/60");
                        if (f.type === "select") {
                          return (
                            <Select value={field.value ?? ""} onValueChange={field.onChange}>
                              <SelectTrigger className={cls}>
                                <SelectValue placeholder={f.placeholder || "Select…"} />
                              </SelectTrigger>
                              <SelectContent>
                                {f.options?.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
                              </SelectContent>
                            </Select>
                          );
                        }
                        if (f.type === "boolean") {
                          return (
                            <div className="flex h-9 items-center">
                              <Switch checked={!!field.value} onCheckedChange={field.onChange} />
                            </div>
                          );
                        }
                        if (f.type === "textarea") {
                          return <Textarea {...field} placeholder={f.placeholder} className={cls} />;
                        }
                        if (f.type === "number") {
                          return <Input type="number" {...field} placeholder={f.placeholder} className={cls} />;
                        }
                        if (f.type === "password") {
                          return <Input type="password" {...field} placeholder={f.placeholder} className={cls} />;
                        }
                        if (f.type === "multiselect") {
                          const arr: string[] = field.value ?? [];
                          return (
                            <div className="flex flex-wrap gap-2 rounded-md border border-input bg-background px-2 py-1.5">
                              {f.options?.map((o) => {
                                const on = arr.includes(o);
                                return (
                                  <button
                                    key={o}
                                    type="button"
                                    onClick={() =>
                                      field.onChange(on ? arr.filter((x) => x !== o) : [...arr, o])
                                    }
                                    className={cn(
                                      "rounded-full border px-2 py-0.5 text-xs transition-colors",
                                      on ? "border-primary bg-primary/15 text-primary" : "border-border text-muted-foreground"
                                    )}
                                  >
                                    {o}
                                  </button>
                                );
                              })}
                            </div>
                          );
                        }
                        return <Input {...field} placeholder={f.placeholder} className={cls} />;
                      }}
                    />
                    {f.help && <div className="text-[11px] text-muted-foreground">{f.help}</div>}
                    {err && <div className="text-[11px] text-destructive">{(err as any).message}</div>}
                  </div>
                );
              })}
            </div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
