import { Component } from '@angular/core';
import { RouterLink, Router} from '@angular/router';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-signup',
  imports: [RouterLink, FormsModule],
  templateUrl: './signup.html',
  styleUrl: './signup.css'
})
export class Signup {
  username: string = '';
  password: string = '';

  constructor(private router: Router) {}

  onSignUp() {
    if (!this.username || !this.password) {
      this.errorMessage = 'Please enter username and password';
      return;
    }

    if (this.password.length < 8) {
      this.errorMessage = 'Password must be at least 8 characters';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const body = {
      username: this.username,
      password: this.password
    };
    
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    this.http.post(`${environment.apiUrl}/users/`, body, { headers }).subscribe({
      next: (response) => {
        this.isLoading = false;
        alert('Account created successfully!');
        this.router.navigate(['/login']);
      },
      error: (error) => {
        this.isLoading = false;
        if (error.status === 400) {
          this.errorMessage = 'Username already exists';
        } else if (error.status === 422) {
          this.errorMessage = 'Invalid input. Please check your username and password.';
        } else {
          this.errorMessage = 'An error occurred. Please try again.';
        }
        console.error('Signup error:', error);
      }
    });
  }
}
