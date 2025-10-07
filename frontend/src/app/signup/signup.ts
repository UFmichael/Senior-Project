// import { Component } from '@angular/core';
// import { RouterLink, Router} from '@angular/router';
// import { FormsModule } from '@angular/forms';

// @Component({
//   selector: 'app-signup',
//   imports: [RouterLink, FormsModule],
//   templateUrl: './signup.html',
//   styleUrl: './signup.css'
// })
// export class Signup {
//   username: string = '';
//   password: string = '';

//   constructor(private router: Router) {}

//   onSignUp() {
//     alert("Username: " + this.username + '\n' + "Password: " + this.password);
//     this.router.navigate(['/login']);
//   }
// }


import { Component } from '@angular/core';
import { RouterLink, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-signup',
  imports: [RouterLink, FormsModule, CommonModule],
  templateUrl: './signup.html',
  styleUrl: './signup.css'
})
export class Signup {
  username: string = '';
  password: string = '';
  errorMessage: string = '';
  isLoading: boolean = false;

  constructor(
    private router: Router,
    private http: HttpClient
  ) {}

  onSignUp() {
    if (!this.username || !this.password) {
      this.errorMessage = 'Please enter username and password';
      return;
    }

    if (this.password.length < 6) {
      this.errorMessage = 'Password must be at least 6 characters';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const body = {
      username: this.username,
      password: this.password
    };

    this.http.post(`${environment.apiUrl}/auth/signup`, body).subscribe({
      next: (response) => {
        this.isLoading = false;
        alert('Account created successfully!');
        this.router.navigate(['/login']);
      },
      error: (error) => {
        this.isLoading = false;
        if (error.status === 400) {
          this.errorMessage = 'Username already exists';
        } else {
          this.errorMessage = 'An error occurred. Please try again.';
        }
        console.error('Signup error:', error);
      }
    });
  }
}
