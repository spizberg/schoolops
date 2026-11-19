import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { ApiService, errorMessage } from '../../core/api';
import { Guardian, Household, Page } from '../../core/models';

@Component({
  selector: 'app-families-page',
  imports: [ReactiveFormsModule],
  templateUrl: './families.page.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FamiliesPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);

  readonly households = signal<Household[]>([]);
  readonly householdTotal = signal(0);
  readonly selectedHousehold = signal<Household | null>(null);
  readonly guardians = signal<Guardian[]>([]);
  readonly guardianSearchResults = signal<Guardian[]>([]);
  readonly guardianSearchTotal = signal(0);
  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly guardianSaving = signal(false);
  readonly error = signal<string | null>(null);
  readonly editingHousehold = signal(false);
  readonly editingGuardianId = signal<string | null>(null);

  readonly householdForm = this.fb.nonNullable.group({
    name: [''],
    address: [''],
    notes: [''],
  });

  readonly householdSearch = this.fb.nonNullable.group({
    q: [''],
  });

  readonly guardianForm = this.fb.nonNullable.group({
    first_name: ['', [Validators.required, Validators.maxLength(100)]],
    last_name: ['', [Validators.required, Validators.maxLength(100)]],
    phone: ['', [Validators.required, Validators.maxLength(40)]],
    email: ['', Validators.email],
    notes: [''],
  });

  readonly guardianSearch = this.fb.nonNullable.group({
    q: [''],
  });

  ngOnInit(): void {
    void this.loadHouseholds();
  }

  async loadHouseholds(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<Household>>('/households', {
          q: this.householdSearch.controls.q.value,
          limit: 100,
        }),
      );
      this.households.set(page.items);
      this.householdTotal.set(page.total);
      const selectedId = this.selectedHousehold()?.id;
      if (selectedId) {
        const refreshed = page.items.find((item) => item.id === selectedId);
        if (refreshed) {
          this.selectedHousehold.set(refreshed);
        }
      }
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.loading.set(false);
    }
  }

  async saveHousehold(): Promise<void> {
    if (this.householdForm.invalid) {
      this.householdForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const value = this.householdForm.getRawValue();
    const payload = {
      name: value.name.trim() || null,
      address: value.address.trim() || null,
      notes: value.notes.trim() || null,
    };
    try {
      const selected = this.selectedHousehold();
      if (this.editingHousehold() && selected) {
        const updated = await firstValueFrom(
          this.api.patch<Household>(`/households/${selected.id}`, payload),
        );
        this.selectedHousehold.set(updated);
      } else {
        const created = await firstValueFrom(
          this.api.post<Household>('/households', payload),
        );
        await this.selectHousehold(created);
      }
      this.cancelHouseholdEdit();
      await this.loadHouseholds();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.saving.set(false);
    }
  }

  async selectHousehold(household: Household): Promise<void> {
    this.selectedHousehold.set(household);
    this.householdForm.setValue({
      name: household.name ?? '',
      address: household.address ?? '',
      notes: household.notes ?? '',
    });
    this.cancelGuardianEdit();
    await this.loadGuardians();
  }

  startEditHousehold(): void {
    this.editingHousehold.set(true);
  }

  cancelHouseholdEdit(): void {
    this.editingHousehold.set(false);
    const household = this.selectedHousehold();
    this.householdForm.reset({
      name: household?.name ?? '',
      address: household?.address ?? '',
      notes: household?.notes ?? '',
    });
  }

  async loadGuardians(): Promise<void> {
    const household = this.selectedHousehold();
    if (!household) {
      return;
    }
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<Guardian>>('/guardians', {
          household_id: household.id,
          limit: 100,
        }),
      );
      this.guardians.set(page.items);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async saveGuardian(): Promise<void> {
    const household = this.selectedHousehold();
    if (!household || this.guardianForm.invalid) {
      this.guardianForm.markAllAsTouched();
      return;
    }
    this.guardianSaving.set(true);
    this.error.set(null);
    const value = this.guardianForm.getRawValue();
    const payload = {
      household_id: household.id,
      first_name: value.first_name,
      last_name: value.last_name,
      phone: value.phone,
      email: value.email.trim() || null,
      notes: value.notes.trim() || null,
    };
    try {
      const id = this.editingGuardianId();
      if (id) {
        await firstValueFrom(this.api.patch<Guardian>(`/guardians/${id}`, payload));
      } else {
        await firstValueFrom(this.api.post<Guardian>('/guardians', payload));
      }
      this.cancelGuardianEdit();
      await this.loadGuardians();
    } catch (error) {
      this.error.set(errorMessage(error));
    } finally {
      this.guardianSaving.set(false);
    }
  }

  startEditGuardian(guardian: Guardian): void {
    this.editingGuardianId.set(guardian.id);
    this.guardianForm.setValue({
      first_name: guardian.first_name,
      last_name: guardian.last_name,
      phone: guardian.phone,
      email: guardian.email ?? '',
      notes: guardian.notes ?? '',
    });
  }

  cancelGuardianEdit(): void {
    this.editingGuardianId.set(null);
    this.guardianForm.reset({
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      notes: '',
    });
  }

  async deleteGuardian(guardian: Guardian): Promise<void> {
    if (!globalThis.confirm(`Delete guardian ${guardian.first_name} ${guardian.last_name}?`)) {
      return;
    }
    this.error.set(null);
    try {
      await firstValueFrom(this.api.delete(`/guardians/${guardian.id}`));
      if (this.editingGuardianId() === guardian.id) {
        this.cancelGuardianEdit();
      }
      await this.loadGuardians();
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async searchGuardians(): Promise<void> {
    this.error.set(null);
    try {
      const page = await firstValueFrom(
        this.api.get<Page<Guardian>>('/guardians', {
          q: this.guardianSearch.controls.q.value,
          limit: 100,
        }),
      );
      this.guardianSearchResults.set(page.items);
      this.guardianSearchTotal.set(page.total);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }

  async openGuardianHousehold(guardian: Guardian): Promise<void> {
    if (!guardian.household_id) {
      this.error.set('This guardian is not attached to a household.');
      return;
    }
    try {
      const household = await firstValueFrom(
        this.api.get<Household>(`/households/${guardian.household_id}`),
      );
      await this.selectHousehold(household);
    } catch (error) {
      this.error.set(errorMessage(error));
    }
  }
}
