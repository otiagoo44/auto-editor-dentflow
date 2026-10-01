import { NextRequest, NextResponse } from "next/server";
import { authorize, HttpError } from "./lib/security";
export function proxy(req: NextRequest) {
  try {
    authorize(req, req.nextUrl.pathname.startsWith("/api/worker/"));
    return NextResponse.next();
  } catch (error) {
    const e = error as HttpError;
    return new NextResponse(e.message, {
      status: e.status || 500,
      headers:
        e.status === 401
          ? {
              "WWW-Authenticate":
                'Basic realm="DentFlow Studio", charset="UTF-8"',
            }
          : {},
    });
  }
}
// API handlers authorize independently. Excluding API avoids Next Proxy buffering
// and truncating local video uploads at its default 10 MB request-body limit.
export const config = {
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico).*)"],
};
