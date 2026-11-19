import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { TokenStore } from './token-store';

export interface CurrentUser {
  id: string;
  email: string;
  role: 'admin' | 'teacher' | 'parent' | 'student';
  is_active: boolean;
  last_login_at: string | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly tokens = inject(TokenStore);
  private readonly _user = signal<CurrentUser | null>(null);

  readonly user = this._user.asReadonly();

  isAuthenticated(): boolean {
    return this.tokens.isAuthenticated();
  }

  async login(email: string, password: string): Promise<void> {
    const response = await firstValueFrom(
      this.http.post<TokenResponse>('/v1/auth/login', { email, password }),
    );
    this.tokens.set(response.access_token);
    try {
      const user = await firstValueFrom(this.http.get<CurrentUser>('/v1/auth/me'));
      this._user.set(user);
    } catch (error) {
      this.tokens.clear();
      throw error;
    }
  }

  logout(): void {
    this.tokens.clear();
    this._user.set(null);
    void this.router.navigate(['/login']);
  }
}
