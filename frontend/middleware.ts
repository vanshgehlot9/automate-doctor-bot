import { NextRequest, NextResponse } from "next/server";

const SESSION_MAP = [
  { prefix: "/vendor", cookie: "vendor_session", login: "/vendor/login" },
  { prefix: "/business", cookie: "business_session", login: "/business/login" },
  { prefix: "/staff", cookie: "staff_session", login: "/staff/login" },
  { prefix: "/super-admin", cookie: "super_admin_session", login: "/super-admin/login" },
  { prefix: "/admin", cookie: "super_admin_session", login: "/super-admin/login" },
];

const ALL_COOKIES = ["vendor_session", "business_session", "staff_session", "super_admin_session"];

function clearCookies(response: NextResponse) {
  for (const cookieName of ALL_COOKIES) {
    response.cookies.set(cookieName, "", { path: "/", maxAge: 0 });
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const route = SESSION_MAP.find((entry) => pathname === entry.prefix || pathname.startsWith(`${entry.prefix}/`));

  if (!route) {
    return NextResponse.next();
  }

  const sessionToken = request.cookies.get(route.cookie)?.value;
  if (sessionToken || pathname === route.login) {
    return NextResponse.next();
  }

  const redirectUrl = request.nextUrl.clone();
  redirectUrl.pathname = route.login;
  redirectUrl.searchParams.set("from", pathname);
  const response = NextResponse.redirect(redirectUrl);
  clearCookies(response);
  return response;
}

export const config = {
  matcher: ["/vendor/:path*", "/business/:path*", "/staff/:path*", "/super-admin/:path*", "/admin/:path*"],
};
