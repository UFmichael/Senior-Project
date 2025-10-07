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
    alert("Username: " + this.username + '\n' + "Password: " + this.password);
    this.router.navigate(['/login']);
  }
}
