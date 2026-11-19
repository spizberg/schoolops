import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  errors?: { msg?: string; loc?: unknown[] }[];
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>;

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/v1';

  get<T>(path: string, params: QueryParams = {}): Observable<T> {
    return this.http
      .get<T>(`${this.base}${path}`, { params: toParams(params) })
      .pipe(catchError(toMessage));
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${this.base}${path}`, body).pipe(catchError(toMessage));
  }

  patch<T>(path: string, body: unknown): Observable<T> {
    return this.http.patch<T>(`${this.base}${path}`, body).pipe(catchError(toMessage));
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<T>(`${this.base}${path}`, body).pipe(catchError(toMessage));
  }

  getBlob(path: string, params: QueryParams = {}): Observable<Blob> {
    return this.http
      .get(`${this.base}${path}`, {
        params: toParams(params),
        responseType: 'blob',
      })
      .pipe(catchError(toMessage));
  }

  delete(path: string): Observable<void> {
    return this.http.delete<void>(`${this.base}${path}`).pipe(catchError(toMessage));
  }
}

function toParams(params: QueryParams): HttpParams {
  let result = new HttpParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      result = result.set(key, String(value));
    }
  }
  return result;
}

function toMessage(error: HttpErrorResponse): Observable<never> {
  return throwError(() => new Error(problemMessage(error)));
}

export function problemMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    const problem = error.error as ProblemDetails | null;
    if (problem?.detail) {
      return problem.detail;
    }
    if (problem?.errors?.length) {
      return problem.errors.map((item) => item.msg ?? 'Invalid value').join('; ');
    }
    return `Request failed (${error.status}).`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unexpected error.';
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unexpected error.';
}
