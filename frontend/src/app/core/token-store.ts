import { Injectable, signal } from '@angular/core';

/**
 * Holds the access token in memory only. Reloading the page logs the user out, as
 * required by ADR-0003; refresh tokens are a phase 2 concern.
 */
@Injectable({ providedIn: 'root' })
export class TokenStore {
  private readonly _token = signal<string | null>(null);

  readonly token = this._token.asReadonly();

  isAuthenticated(): boolean {
    return this._token() !== null;
  }

  set(token: string): void {
    this._token.set(token);
  }

  clear(): void {
    this._token.set(null);
  }
}
