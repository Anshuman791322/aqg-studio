import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabaseUrl =
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder-project.supabase.co";
  const supabaseKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    "placeholder-anon-key";

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: Array<{ name: string; value: string; options?: CookieOptions }>) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        response = NextResponse.next({
          request,
        });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        );
      },
    },
  });

  // Refresh auth token
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isAuthRoute = request.nextUrl.pathname.startsWith("/auth");
  const isProtectedRoute =
    request.nextUrl.pathname.startsWith("/dashboard") ||
    request.nextUrl.pathname.startsWith("/assessments") ||
    request.nextUrl.pathname.startsWith("/documents");

  // Redirect unauthenticated users attempting to access protected routes
  if (!user && isProtectedRoute) {
    const returnUrl = encodeURIComponent(request.nextUrl.pathname + request.nextUrl.search);
    const redirectUrl = new URL(`/auth/sign-in?returnUrl=${returnUrl}`, request.url);
    return NextResponse.redirect(redirectUrl);
  }

  // Redirect authenticated users away from sign-in/sign-up to returnUrl or dashboard
  if (
    user &&
    isAuthRoute &&
    (request.nextUrl.pathname === "/auth/sign-in" ||
      request.nextUrl.pathname === "/auth/sign-up")
  ) {
    const rawReturnUrl = request.nextUrl.searchParams.get("returnUrl");
    const safeTarget =
      rawReturnUrl && rawReturnUrl.startsWith("/") && !rawReturnUrl.startsWith("//")
        ? rawReturnUrl
        : "/dashboard";
    const redirectUrl = new URL(safeTarget, request.url);
    return NextResponse.redirect(redirectUrl);
  }

  return response;
}
